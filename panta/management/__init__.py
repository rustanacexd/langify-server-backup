from django.db import transaction
from django.utils import timezone
from panta.constants import (
    BLANK,
    CHANGE_REASONS,
    HISTORICAL_UNIT_PERIOD,
    IN_REVIEW,
    IN_TRANSLATION,
    REVIEW_DONE,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)
from panta.utils import get_system_user


class Segments:
    # The method is to create the historical records (hr) afterwards
    #
    # A description of what is done in this function but it is implemented
    # more database efficient.
    # 1. admin creates translated work
    #    -> this creates segment
    #    -> this creates the first hr (without user info)
    # 2. user edits segment
    # 3. first draft comes in, is processed and saved without hr (#1)
    # 4. second draft -> is saved without hr (#2)
    # 5. user leaves segment (i.e. clicks into another segment or 3 min pass)
    # 6. unlock segment, check if most recent hr is an edit and differs from
    #    the content of the segment, is of the same user, in period x and has
    #    no votes (#3, #4, #5),
    #     - if positive:
    #         1. determine and set the change reason and the amount of changes
    #            on the basis of the segment and the hr before the most
    #            recent one,
    #         2. save hr and (#6)
    #         3. save segment without hr (#7),
    #     - if negative: create hr (i.e.
    #         1. determine and set the change reason and the amount of changes
    #            on basis of the segment and the most recent hr,
    #         2. set the user who locked the segment as user info in the hr and
    #         3. call `save`, #6, #7?)
    #     - determine the current translation progress
    # 7. procedure begins with 2
    #
    # Database queries: 7

    def __init__(self):
        self.states = {
            state: []
            for state in (
                BLANK,
                IN_TRANSLATION,
                TRANSLATION_DONE,
                IN_REVIEW,
                REVIEW_DONE,
                TRUSTEE_DONE,
            )
        }

    @transaction.atomic
    def conclude(self, queryset):
        """
        Unlocks segments, updates the progress and updates the history.
        """
        # TODO reduce queries and content
        # TODO maybe remove this filter to not silence errors
        queryset = queryset.filter(locked_by__isnull=False)
        pks = queryset.values_list('id', flat=True)
        history = queryset.model.history.filter(
            id__in=pks,
            # history_date__gte=timezone.now()-HISTORICAL_UNIT_PERIOD,
        )
        history = history.order_by('-history_date').select_for_update()
        # annotate has to be added after calls of values_list
        queryset = queryset.add_2_votes()
        most_recent_history = {}
        next_recent_history = {}
        records = {'new': 0, 'updated': 0}
        ai_user = None

        for obj in history:
            if obj.id not in most_recent_history:
                most_recent_history[obj.id] = obj
            elif obj.id not in next_recent_history:
                next_recent_history[obj.id] = obj

        for segment in queryset:
            past = most_recent_history.get(segment.pk)
            if past is None:
                # Don't create a historical record if user didn't do anything
                if segment.content == '':
                    continue
                latest = None
                history_obj = self.create_history_obj(segment)
            else:
                change_reason = past.history_change_reason
                if change_reason:
                    # Check if the most recent historical record is an edit
                    is_delete = change_reason == CHANGE_REASONS['delete']
                    restore = CHANGE_REASONS['restore'].split('#')[0]
                    is_restore = change_reason.startswith(restore)
                    is_edit = not is_delete and not is_restore
                    # Check if last edit was from same user and quite recent
                    same_user = past.history_user_id == segment.locked_by_id
                    date = past.history_date + HISTORICAL_UNIT_PERIOD
                    in_period = date >= segment.last_modified
                    votes = past.votes.exists()
                else:
                    is_edit = False

                if is_edit and same_user and in_period and not votes:
                    # Reuse the last history entry compare to the one before
                    latest = next_recent_history.get(segment.pk)
                    history_obj = past
                else:
                    latest = past
                    history_obj = self.create_history_obj(segment)

            # Check that content differs
            if latest is None or segment.content != latest.content:
                # Set change reason
                if latest is None or latest.content == '':
                    change_reason = CHANGE_REASONS['new']
                elif segment.content == '':
                    change_reason = CHANGE_REASONS['delete']
                else:
                    change_reason = CHANGE_REASONS['change']
                    # TODO Distinguish between small and bigger edits,
                    # i.e. typo, word, sentence.
                    # https://docs.python.org/3/library/difflib.html
                    # #sequencematcher-examples

                # Set outstanding fields and save history object
                history_obj.history_date = segment.last_modified
                history_obj.history_change_reason = change_reason
                history_obj.content = segment.content
                # TODO set the +es an -es

                if history_obj.pk:
                    records['updated'] += 1
                else:
                    records['new'] += 1

                history_obj.save()

                # Determine the progress
                self.add_to_update_list(segment)

            else:
                # Check if the user accepted an AI translation without change
                if ai_user is None:
                    ai_user = get_system_user('AI')
                if latest.history_user_id == ai_user.pk:
                    # Determine the progress
                    self.add_to_update_list(segment)

        # Unlock segments
        count = 0
        for state, pks in self.states.items():
            count += queryset.filter(pk__in=pks).update(
                locked_by_id=None, progress=state, last_modified=timezone.now()
            )
        # No progress update required
        # todo: Remove this? See comment in "add_to_update_list"
        if count < len(queryset):
            count += queryset.filter(locked_by__isnull=False).update(
                locked_by_id=None, last_modified=timezone.now()
            )
        records['unlocked'] = count
        return records

    def create_history_obj(self, segment):
        # Set the desired fields
        historical_segment = segment.add_to_history(
            # The segment will never be created (+) or deleted (-) here
            history_type='~',
            history_user=segment.locked_by,
            # "relative_id" is calculated in "save"
            save=False,
        )
        return historical_segment

    def add_to_update_list(self, segment):
        """
        Calculates the completion of a segment and adds its ID to the list.
        """
        # Segments where the progress didn't change are included because it
        # otherwise resulted in another query (an update for these segments).
        # Furthermore, the progress changes most of the time.

        # States when the current one is "in tr.", "tr. done" or "in rev."
        # Previous         | Next
        # -----------------|-----------
        # blank            | current
        # in translation   | current
        # translation done | current
        # in review        | in review
        # review done      | in review
        # trustee done     | in review

        progress = segment.determine_progress()
        # todo: We could check if progress < IN_REVIEW and calculate the
        # progress in this case only (with determine_progress(votes=False)).

        set_to_in_review = (
            # Blank segments should always be in state "blank"
            progress != BLANK
            # Segments that have never been "in review" or above should always
            # be in the calculated current state
            and segment.progress > TRANSLATION_DONE
            # Segments with completed approvals should always be in the
            # calculated current state, too
            and progress <= IN_REVIEW
        )
        if set_to_in_review:
            # - Don't downgrade below "in review" to allow reviewers+ only to
            #   edit after once "in review" or above
            # - Downgrade to "in review" if somebody edited a segment in a
            #   higher state
            progress = IN_REVIEW

        self.states[progress].append(segment.pk)
