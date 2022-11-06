# Permissions

## General permissions

Django calls it permissions. In general we have these permissions:

- view
- add
- change
- delete
- history (view only)

We have to apply these (and other) permissions to every model object and user.
The models are listed below (see *Details*).

## Systems

Permissions are implemented differently:

### Views

If a permission depends on a HTTP method (`GET`, `PUT`, `PATCH`, `DELETE`) only or if the user is authenticated or not it is easy to deny access on this level.

### Serializers

View, read and write permissions on a field level should be implemented in serializers. If they are applied for all users there is no need to use another permission system.

### Object permissions

Used where different users have different permissions for different objects of the same model.

### Model permissions

Similar to object permissions but on a model level. For instance when adding objects of models with object permissions.

### Reputation score

Users need reputation for the action.

### ObjectPermissions

Authenticated users are allowed to view objects. There is no need for model or object permissions. Therefore it is implemented as special case in the `ObjectPermissions` class.

### Admin

The admin doesn't use the API. Therefore it requires another implementation if the checks are done in API classes (i.e. views, serializers and permissions modules).

## Details

Each headline represents a model.

"user" means an authenticated user.

"admin" means this is done in the admin area. This applies to almost every
permission below but is not mentioned explicitly everywhere.

### User

✅ | Permission | User | System
---|------------|------|-------
✅ | view `id` | admin | serializers, templates
✅ | view username | users\* | permissions
✅ | view password | nobody | hashed, serializers, admin
✅ | view pseudonym | admin | serializers
⬜️ | view contact details | owner\* | serializers
⬜️ | view most fields | users/owner | serializers, permissions
⬜️ | view reputation | owner, Moderator | ?
⬜️ | view privileges | users? | ?
⬜️ | view contributions | users? | ?
⬜️ | view information of deleted users | admin | API view, serializers
✅ | add | anonymous user | signup view, serializers
✅ | change | owner | serializers
✅ | change username | admin | serializers
✅ | change `public_id` | shell | serializers, admin
✅ | delete | owner | serializers
✅ | history | admin | serializers

\* = Every user can guess usernames and e-mail addresses using the signup or send e-mail confirmation endpoints.

Note that there are two serializers so far: `UserSerializer` and `UserFieldSerializer`. All relations to the user object are represented by latter in the API.

Inactive users are invisible in the API.

### Reputation

todo

### E-mail address

todo

### E-mail confirmation

todo

### Social account

todo

### Social app

todo

### Social token

todo

### Privilege (obsolete)

Besides these permissions everybody can see how privileges are defined (but that's not important here).

✅ | Permission | User
---|-----------|------
⬜️ | view | admin
⬜️ | add | Trustee
⬜️ | change | admin
⬜️ | delete | Trustee

Trustee because they can define the languages a work should be translated in to.

System: accessed indirectly

### Trustee

Note: **Trustees will be re-named and get another meaning.**

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | ObjectPermissions
✅ | add | admin | views
✅ | change | staff | object permissions
✅ | change code | admin | serializers
✅ | delete | staff | object permissions
✅ | history | admin | views, serializers
⬜️ | historical records | history user | serializer

Groups:

- `<code>-staff`
- ~`<code>-members`~

### Original work

✅ | Permission | User | System
---|------------|------|-------
✅ | view | everybody | permissions
⬜️ | view private | member | ?
✅ | add | user | ObjectPermissions
✅ | change | staff (Trustee) | object permissions
✅ | change abbreviation | admin | serializers
✅ | change tags | admin | serializers
✅ | limit trustee | staff (Trustee) | object permissions (serializers)
✅ | delete | owner (Trustee) | OriginalWorkPermissions
⬜️ | history | user | ?
⬜️ | historical records | history user | serializer

### Translated work

✅ | Permission | User | System
---|------------|------|-------
✅ | view | everybody | permissions
⬜️ | view private | member | ?
✅ | add | admin | serializers (read only fields)
✅ | change | staff (Trustee) | object permissions
✅ | change abbreviation | admin | serializers
✅ | change type | admin | serializers
✅ | change language | admin | serializers
✅ | change trustee | admin | serializers
✅ | change private | admin | serializers
✅ | change original | admin | serializers
✅ | change protected | admin | serializers
✅ | change tags | admin | serializers
✅ | delete | admin | protected by segments
✅ | switched segments | user | reputation score (permissions)
⬜️ | history | user | ?
⬜️ | historical records | history user | serializer

### Author

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | DjangoObjectPermissions 
⬜️ | view private | member | ?
✅ | add | admin | model permissions
✅ | change | admin | object permissions
✅ | delete | admin | object permissions
✅ | history | admin | views, serializers
⬜️ | historical records | history user | serializer

To decide: Do we have general authors (filtering more reliable) or can every responsible entity have their own or a combination of both?

### Licence

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | DjangoObjectPermissions
✅ | add | admin | model permissions
✅ | change | admin | object permissions
✅ | delete | admin | object permissions
✅ | history | admin | views, serializers
⬜️ | historical records | history user | serializer

### Release

Not yet implemented.

✅ | Permission | User | System
---|------------|------|-------
⬜️ | view | user | ObjectPermissions
⬜️ | view private | member | ?
⬜️ | add | user | reputation score
⬜️ | change | admin | model permissions
⬜️ | delete | admin | model permissions
⬜️ | history | admin | views, serializers

### Original segment

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | ObjectPermissions
✅ | view `key` | admin | serializers
⬜️ | view private | members | ?
✅ | add | admin | views, serializers
⬜️ | add via work | staff (Trustee) | ?
✅ | change | admin | serializers, object permissions 
✅ | change position | admin | serializers
✅ | change page | admin | serializers
✅ | change tag | admin | serializers
✅ | change classes | admin | serializers
✅ | change content | admin | serializers
✅ | change reference | admin | serializers
✅ | change work | admin | serializers
✅ | delete | admin | views
⬜️ | history | user | ?
⬜️ | historical records | history user | serializer

### Translated segment

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | ReputationPermissions
⬜️ | view private | members | ?
✅ | add | admin | views
⬜️ | add via work | ? | ?
✅ | change | admin | views
✅ | delete | admin | views
✅ | delete content | user | reputation score (permissions)
✅ | undo | person responsible | reputation score (permissions)
✅ | restore | user | reputation score (views)
⬜️ | review | *new* trustee | reputation score
✅ | history | user | IsAuthenticated, views
⬜️ | historical records | history user | serializer

### Vote

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | ReputationPermissions
⬜️ | view private | members | ?
✅ | add | user | ReputationPermissions
✅ | change | admin | views
✅ | delete | admin | views

### Base translation

(and related models)

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | translated segment field
✅ | add | admin/shell | serializer
✅ | change | admin/shell | serializer
✅ | delete | admin | serializer


### Segment draft

✅ | Permission | User | System
---|------------|------|-------
✅ | view | owner | views
✅ | add | user | reputation score (permissions)
✅ | set created | admin | serializers
✅ | set work | admin | views, serializers
✅ | set position | admin | views, serializers
✅ | set owner | admin | views, serializers
⬜️ | limit segment | user | ?
✅ | change | admin | views
✅ | delete | admin | views

### Reference

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | DjangoObjectPermissions
⬜️ | view private | members | ?
✅ | add | admin | model permissions
✅ | change | admin | object permissions
✅ | delete | admin | object permissions
⬜️ | historical records | history user | serializer

To decide: Do we have general references or can every responsible entity have their own or a combination of both? What about a history?

### Segment comment

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | ReputationPermissions
⬜️ | view private | members | ?
✅ | add | user | reputation score (permissions)
✅ | change | owner | reputation score (permissions)
✅ | change `work` | admin | serializers
✅ | change `position` | admin | serializers
✅ | change `user` | admin | serializers
✅ | change `vote` | admin | serializers
✅ | change `to_delete` | user via `delete` | serializers
⬜️ | limit work | user | ?
✅ | delete | owner | reputation score (permissions)

### Developer comment

✅ | Permission | User | System
---|------------|------|-------
✅ | view | user | permissions
✅ | add | user | permissions
✅ | change | owner | permissions
✅ | change `user` | admin | serializers
✅ | change `to_delete` | user via `delete` | serializers
✅ | delete | owner | permissions

### Page

✅ | Permission | User | System
---|------------|------|-------
✅ | view | everybody/user | permissions
✅ | view `content` | admin | serializers
✅ | view `protected` | everybody | serializers, views (redirect)
✅ | add | admin | views
✅ | change | admin | views
✅ | delete | admin | views
✅ | history | admin | views, serializers
⬜️ | historical records | history user | serializer

### Log entry

✅ | Permission | User | System
---|------------|------|-------
⬜️ | view | admin, executing user | serializer
✅ | add | shell | views
✅ | change | shell | views
✅ | delete | shell | views

### Session

✅ | Permission | User | System
---|------------|------|-------
⬜️ | view except `session_data` | owner | serializer
✅ | add | shell | views
✅ | change | shell | views
✅ | delete | shell | views

### Other models

These models don't have a JSON API.

- White Estate
- Site
- Content type
- (Object) permissions

### Internal statistics

Users with the permission `misc.view_page`

### External APIs

#### Newsletter2Go

Everybody can add an e-mail, name and language
