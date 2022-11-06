from frontend_urls import OAUTH_CALLBACK

AUTHORIZE_URL = 'https://cpanel.egwwritings.org/o/authorize/'

TOKEN_URL = 'https://cpanel.egwwritings.org/o/token/'

API_URL = 'https://a.egwwritings.org/'

USER_PROFILE_URL = '{0}user/info/'.format(API_URL)

CALLBACK_URL = '/' + OAUTH_CALLBACK.format(provider='white-estate')

# Book lists

CONFLICT_OF_THE_AGES_SERIES = (
    'Patriarchs and Prophets',
    'Prophets and Kings',
    'The Desire of Ages',
    'The Acts of the Apostles',
    'The Great Controversy',
)

GROWING_TOGETHER_SERIES = CONFLICT_OF_THE_AGES_SERIES + (
    'Christian Service',
    'Christ’s Object Lessons',
    'Counsels for the Church',
    'Counsels on Stewardship',
    'The Ministry of Healing',
    'Steps to Christ',
    'The Story of Redemption',
)

# Note that empty manuscripts are excluded during the import process
EMPTY_WORKS = ('Christ Our Saviour',)

WORKS_WITH_YOUNGER_EDITION = (
    'Gospel Workers 1892',
    'The Great Controversy 1888',
    'Life Sketches of James White and Ellen G. White 1880',
)

EXISTING_WORKS = {
    # Source: EGW app
    'am': (
        'Counsels for the Church',  # የቤተ ፡ ክርስቲያን፡ ምክሮች፡፡ (CCh)
        'Education',  # ሥነ - ትምህርት (EDA)
        # "እግዚአብሄር ቃል ገብቷል" (እቃገ) not found
        # "ታላቁ ተስፋ" (ታተ) not found (seems to be parts of GC or GrH_c)
        'Steps to Christ',  # ወደ ክርስቶስ የሚመራ መንገድ (ክየመ)
    ),
    # Source: Jesse
    'ar': GROWING_TOGETHER_SERIES
    + (
        # Source: EGW app
        # "المَبَادئُ الأسَاسِيَّةُ - لِلِإصْلاَحِ الصِّحِّىِّ" (BHA) not found
        'Education',  # التربيـــة (Tr)
        # "The Ministry of Healing" is "خدمة الشفاء" (KS)
        # "Patriarchs and Prophets" is "الاباء والانبياء" (AA)
        # "The Acts of the Apostles" is "أعما لالرُّسل" (AR)
    ),
    'ber': (),
    # Source: Jesse
    'ckb': ('Steps to Christ',),
    # Source: EGW app
    'cs': (
        'Steps to Christ',  # Cesta ke Kristu (CK)
        # Steps to Jesus, Cesta k vnitřnímu pokoji (CVP) (Modern English)
        'A Call to Medical Evangelism and Health Education',  # Dobrá zpráva
        # pro tělo i ducha (Povolání ke zdravotní evangelizaci a výchově ke
        # zdraví) (DZ)
        'Thoughts From the Mount of Blessing',  # Myšlenky o naději (MON)
        # Modlitba za nemocné (MZN) not found, seems to be not available in
        # English
        'The Story of Jesus',  # Naděje lidstva (NL)
        'From Eternity Past',  # Na úsvitu dějin (NUD)
        'Prophets and Kings',  # Proroci a králové (PK)
        'Christ’s Object Lessons',  # Perly moudrosti (PM)
        'Colporteur Ministry',  # Poslové naděje (PN)
        'The Acts of the Apostles',  # Poslové naděje a lásky (PNL),
        #                              POSLOVÉ NADĚJE A LÁSKY (PNL)
        'Patriarchs and Prophets',  # Patriarchové a proroci (PP)
        'Last Day Events',  # Poslední dny planety země (PPZ)
        'Counsels for the Church',  # Rady pro církev (RPC)
        'From Splendor to Shadow',  # Od slávy k úpadku (SU)
        'The Desire of Ages',  # Touha věků (TV)
        'Education',  # Výchova (Vy)
        'The Great Controversy',  # Velké drama věků (VDV)
        'The Ministry of Healing',  # Život naplněný pokojem (ZNP)
        'Christian Service',  # KŘESŤANSKÁ SLUŽBA (KS)
    ),
    # Source: xslx file (in Dropbox)
    'de': CONFLICT_OF_THE_AGES_SERIES
    + (
        'The Adventist Home',
        'An Appeal to Mothers',
        'An Appeal to the Youth',
        'A Call to Medical Evangelism and Health Education',
        'Christ in His Sanctuary',
        'Child Guidance',
        'Christ’s Object Lessons',
        'Christian Service',
        'Christian Temperance and Bible Hygiene',
        'Christ Triumphant',
        'Colporteur Ministry',
        # 'Communion With God', Not part of the EGW writings
        'Counsels on Diet and Foods',
        'Counsels on Sabbath School Work',
        'Counsels on Stewardship',
        'Country Living',
        'Evangelism',
        'Early Writings',
        'Education',
        'Faith and Works',
        # 'God Has Promised', Not available at egwwritings.org
        'Gospel Workers 1915',
        # 'Happiness Homemade', Not found
        'Last Day Events',
        'Letters to Young Lovers',
        # 'Life at its best', Not found
        'Life Sketches of Ellen G. White',
        'Maranatha',
        ('Messages to Young People', 'MYP'),
        'Mind, Character, and Personality, vol. 1',
        'Mind, Character, and Personality, vol. 2',
        'The Ministry of Healing',
        'Ministry to the Cities',
        'A New Life (Revival and Beyond)',
        'Prayer',
        'The Sanctified Life',
        'Selected Messages Book 1',
        'Selected Messages Book 2',
        'Spiritual Gifts, vol. 1',
        'SDA Bible Commentary, vol. 7A (EGW)',
        'Steps to Christ',
        'Temperance',
        # 'Testimonies for Ministers', Not found
        'Testimonies for the Church, vol. 1',
        'Testimonies for the Church, vol. 2',
        'Testimonies for the Church, vol. 3',
        'Testimonies for the Church, vol. 4',
        'Testimonies for the Church, vol. 5',
        'Testimonies for the Church, vol. 6',
        'Testimonies for the Church, vol. 7',
        'Testimonies for the Church, vol. 8',
        'Testimonies for the Church, vol. 9',
        'Testimony Treasures, vol. 1',
        'Testimony Treasures, vol. 2',
        'Testimony Treasures, vol. 3',
        'The Story of Redemption',
        'Thoughts From the Mount of Blessing',
        'The Truth About Angels',
        'Ye Shall Receive Power',
    ),
    # Source: EGW app
    'fa': (
        'Steps to Christ',  # گامهایی بسوی نور (GBN)
        'The Desire of Ages',  # آرزوی اعصار (AA)
        'Patriarchs and Prophets',  # پاتریاخها و انبیا (PA)
        'Testimonies for the Church, vol. 1',  # شهادتهایی برای کلیسا — جلد اول
        #                                       (SBK1)
        'Child Guidance',  # تعلیم و تربیت کودک (TTK)
        'Christ’s Object Lessons',  # حکایتهای پند آموز مسيح (HAM)
    ),
    # Source:
    # http://www.ellenwhitecenter.org/ellen-white/bibliographie/ellen-white
    'fr': CONFLICT_OF_THE_AGES_SERIES
    + (
        'Spiritual Gifts, vol. 1',
        'Early Writings',
        'The Great Controversy 1888',
        'Christian Temperance and Bible Hygiene',
        'Gospel Workers 1892',
        'Steps to Christ',
        'The Story of Jesus',
        'Thoughts From the Mount of Blessing',
        'Christ’s Object Lessons',
        'Testimonies on Sabbath-School Work',
        'Education',
        'The Ministry of Healing',
        'Counsels to Parents, Teachers, and Students',
        'Gospel Workers 1915',
        'Life Sketches of Ellen G. White',
        'The Colporteur Evangelist',
        'Christian Service',
        ('Messages to Young People', 'MYP'),
        'Counsels on Diet and Foods',
        'Counsels on Stewardship',
        'Evangelism',
        'The Story of Redemption',
        'Temperance',
        'Testimony Treasures, vol. 1',
        'Testimony Treasures, vol. 2',
        'Testimony Treasures, vol. 3',
        'My Life Today',
        'The Adventist Home',
        'Welfare Ministry',
        'Colporteur Ministry',
        'Selected Messages Book 1',
        'Selected Messages Book 2',
        'That I May Know Him',
        'God\'s Amazing Grace',
        'Mind, Character, and Personality, vol. 1',
        'Mind, Character, and Personality, vol. 2',
        'The Upward Look',
        'Testimonies on Sexual Behavior, Adultery, and Divorce',
        'Last Day Events',
        'Ye Shall Receive Power',
        'Christ Triumphant',
    ),
    # Source: EGW app
    'hi': (
        'Spiritual Gifts, vol. 1',  # महान संघर्ष (1SG, GCH, duplicate)
        'Steps to Christ',  # ख्रीष्ट की और कदम (SC)
    ),
    # Source: Péter Erdődi, Zsuzsa Kökényes (Advent Publishing House, Budapest)
    'hu': CONFLICT_OF_THE_AGES_SERIES
    + (
        # From the Hungarian Union's publishing house (Advent Kiadó)
        # Patriarchs and Prophets  (Pátriárkák és próféták) Advent Kiadó, 1993
        # Prophets and Kings  (Próféták és királyok) Advent Kiadó, 1981
        # The Desire of Ages  (Jézus élete) Élet és Egészség Kiadó, 2004
        # The Acts of the Apostles  (Az apostolok története) Advent Kiadó, 1978
        # The Great Controversy  (A nagy küzdelem) Advent Kiadó, 1986
        'The Story of Redemption',  # (A megváltás története) Advent Kiadó, 2000
        'Selected Messages Book 1',  # (Szemelvények E. G. White írásaiból, 1.
        #                              kötet) Advent Kiadó, 1999
        'Selected Messages Book 2',  # (Szemelvények E. G. White írásaiból, 2.
        #                              kötet) Advent Kiadó, 2000
        'Selected Messages Book 3',  # (Szemelvények E. G. White írásaiból, 3.
        #                              kötet) Advent Kiadó, 2010
        "God's Amazing Grace",  # (Isten csodálatos kegyelme) Advent Kiadó, 03
        'Ye Shall Receive Power',  # (A Szentlélek eljő reátok) Advent Kiadó, 95
        'The Ministry of Healing',  # (A Nagy Orvos lábnyomán) Advent Kiadó, 01
        'The Adventist Home',  # (Boldog otthon) Advent Kiadó, 1998
        'Gospel Workers 1915',  # (Az evangélium szolgái) Advent Kiadó
        'Evangelism',  # (Evangelizálás) Advent Irodalmi Műhely & Felfedezések
        #                Alapítvány, 2007
        'Education',  # (Nevelés) Advent Kiadó, 2015
        'Letters to Young Lovers',  # (Levelek szerelmes fiataloknak) Advent
        #                             Kiadó, 1995
        'Last Day Events',  # (Az utolsó napok eseményei) Felfedezések
        #                     Alapítvány, 2007
        'Steps to Christ',  # (Jézushoz vezető út) Advent Kiadó, 2013
        'Christ’s Object Lessons',  # (Krisztus példázatai) Advent Kiadó, 1999
        'True Revival',  # (Az igazi megújulás) Advent Kiadó, 2011
        #
        # From the Romanian Union's publishing house (Viață și Sănătate)
        'Child Guidance',  # (Gyermeknevelés) Viață și Sănătate, 2018
        'Reflecting Christ',  # (Krisztusi élet) Viață și Sănătate, 2009
        'Prayer',  # (Az imádság) Viață și Sănătate, 2018
        #
        # From an independent publishing house (B. I. K.)
        'Testimonies for the Church, vol. 5',  # (Bizonyságtételek 5. kötet)
        #                                        BIK Kiadó, 2001
        ('Messages to Young People', 'MYP'),  # (Üzenet az ifjúságnak) BIK
        #                                       Kiadó, 2002
        'Early Writings',  # (Korai írások) BIK Kiadó, 2006
        'Christian Leadership',  # (Keresztény vezetés) BIK Kiadó, 2014
    ),
    # Source: EGW app
    'id': CONFLICT_OF_THE_AGES_SERIES
    + (
        'Steps to Christ',
        'Early Writings',
        'Child Guidance',
        'Christ’s Object Lessons',
        'The Adventist Home',
        'The Ministry of Healing',  # MEMBINA KELUARGA SEHAT (MKS)
        'Education',
        'Counsels on Diet and Foods',
        'Gospel Workers 1915',
        'Last Day Events',
        'Thoughts From the Mount of Blessing',
        'Counsels for the Church',  # Nasihat Bagi Sidang (NBS)
        'Letters to Young Lovers',  # SURAT KASIH BAGI PASANGAN MUDA (SPM)
        ('Messages to Young People', 'MYP'),  # Amanat Kepada Orang Muda Lengkap
        #                                       (AML)
        'Christian Leadership',  # Sukses Memimpin (SM)
        'Testimonies on Sexual Behavior, Adultery, and Divorce',  # Nasihat
        #            Mengenai Perilaku Seksual, Perzinahan Dan Perceraian (NMPS)
        # I couldn't find this book in English: Malaikat Lain (ML)
        # "Prophets and Kings" is "Para Nabi Dan Raja" (PR)
    ),
    # Source: EGW app
    'it': CONFLICT_OF_THE_AGES_SERIES
    + (
        # Books
        'The Voice in Speech and Song',  # LA VOCE NEL LINGUAGGIO E NEL CANTO
        #                                  (VLC)
        'Colporteur Ministry',
        'Counsels on Diet and Foods',
        'Counsels on Stewardship',
        'God’s Remnant Church (The Remnant Church)',  # La chiesa del rimanente
        #                                               (CR)
        'The Adventist Home',
        'Thoughts From the Mount of Blessing',
        ('Messages to Young People', 'MYP'),
        'The Ministry of Healing',
        'Education',
        'Early Writings',
        'Christ’s Object Lessons',
        'Christian Service',
        'Testimony Treasures, vol. 1',
        'Testimony Treasures, vol. 2',
        'Testimony Treasures, vol. 3',
        'Last Day Events',
        'Steps to Christ',
        'Testimonies to Ministers and Gospel Workers',  # Testimonianze Per I
        #                           Ministri E Per Gli Operai Del Vangelo (TMGI)
        'The Truth About Angels',  # LA VERITÀ SUGLI ANGELI (VA)
        'Selected Messages Book 1',  # MESSAGGI SCELTI, vol. 1 (MS1)
        'Selected Messages Book 2',  # MESSAGGI SCELTI, vol. 2 (MS2)
        'Selected Messages Book 3',  # MESSAGGI SCELTI, vol. 3 (MS3)
        'Christ in His Sanctuary',  # GESÙ NEL SUO SANTUARIO (GSS)
        'Temperance',  # LA TEMPERANZA (LTI)
        'Prayer',  # LA PREGHIERA (LP)
        # Devotionals
        'The Upward Look',  # Volgi lo sguardo a Gesù (VG)
        "God's Amazing Grace",  # STUPENDA GRAZIA DI DIO (SGD)
        'Reflecting Christ',  # CONTEMPLARE LA VITA DI CRISTO (CC)
        'Christ Triumphant',  # LA VITTORIA DI CRISTO (VC)
        'Maranatha',  # Maranatha (Mar)
        'The Faith I Live By',  # Vivere Attraverso La Fede (VAF)
    ),
    # Source: EGW app
    'nb': (
        'Early Writings',  # Det er et godt land (DEEGL),
        #                    Herren Har Vist Meg… (HH)
        'The Adventist Home',  # Det Kristne hjem (DKH)
        'Gospel Workers 1915',  # EVANGELIETS TJENERE (ET),
        #                         Evangeliets tjenere (EVTJ)
        'The Ministry of Healing',  # Helse og livsglede (HOL)
        # "Jorden opplyst" (JOP) not found
        'The Great Controversy',  # Mot historiens klimaks (MHK)
        'Christ’s Object Lessons',  # Ord som lever (OSLv)
        'Selected Messages Book 1',  # På fast grunn 1 (PFG1)
        'Selected Messages Book 2',  # På fast grunn 2 (PFG2)
        'Counsels on Diet and Foods',  # Råd og vink (ROV)
        'The Desire of Ages',  # Slektenes Håp (SH)
        'Testimony Treasures, vol. 1',  # Veiledning for menigheten 1. bd.
        #                                 (VFM1)
        'Testimony Treasures, vol. 2',  # Veiledning For Menigheten, vol. 2
        #                                 (VM2)
        'Testimony Treasures, vol. 3',  # Veiledning For Menigheten, vol. 3
        #                                 (VFM3)
        'Steps to Christ',  # Veien til Kristus (VTK)
        ('Messages to Young People', 'MYP'),  # Ung i dag (UD, UID)
        'The Acts of the Apostles',  # Apostlenes Liv og Virksomhed (AV)
        'The Story of Jesus',  # Kristus vår Frelser (KF)
    ),
    # Source: Jesse
    'sw': CONFLICT_OF_THE_AGES_SERIES
    + (
        # Source: EGW app
        # "The Great Controversy" is "Pambano Kuu" (TU)
        'From Heaven With Love',  # Tumaini la Vizazi Vyote (TVV)
        'From Here to Forever',  # TANGU SASA HATA MILELE (TSHM)
        'Maranatha',  # Maranatha (MarSwh)
        'Steps to Christ',  # KUMJUA YESU (KY),
        #                     HATUA ZA UKAMILIFU KATIKA KRISTO (HUK)
        # Source: Jesse/Ufunou Publishing House (UPH)
        'Christ’s Object Lessons',
        'Counsels for the Church',
        'Christian Service',
        'Colporteur Ministry',
        'Counsels on Stewardship',
        'Education',
        'In Heavenly Places',
        'Last Day Events',
        'Letters to Young Lovers',
        'Our High Calling',
        'Sons and Daughters of God',
        'The Great Hope (Condensed)',
        'Ye Shall Receive Power',
    ),
    'tl': (
        # Books,
        'Acts of Apostles',
        'Christ’s Object Lessons',
        'Ministry of Healing',
        'Patriarchs and Prophets',
        'Prophets and Kings',
        'Steps to Christ',
        'The Colporteur Evangelist',
        'The Desire of Ages',
        'The Great Controversy',
    ),
    'pl': ('Sons and Daughters of God', 'Christian Leadership'),
    # Source: EGW app
    'uk': CONFLICT_OF_THE_AGES_SERIES
    + (
        # Books
        'Spiritual Gifts, vol. 1',
        'Education',
        ('Messages to Young People', 'MYP'),
        'Steps to Christ',
        'The Story of Redemption',
        'Letters to Young Lovers',
        'Christ’s Object Lessons',
        'Thoughts From the Mount of Blessing',
        'Darkness Before Dawn',  # Перемога Божої любові (ПБЛ)
        'Counsels on Diet and Foods',
        'The Ministry of Healing',
        'The Adventist Home',
        'Christian Service',
        'The Time and The Work',
        'What Shall We Teach?',
        # Devotionals
        'In Heavenly Places',
        'From the Heart',
        'Reflecting Christ',
        'Maranatha',  # 4 volumes
        'To Be Like Jesus',
        'Lift Him Up',
        'Our High Calling',
        'Christ Triumphant',
        'This Day With God',
        'That I May Know Him',
    ),
    # Source: docx file (in Dropbox)
    'zh': CONFLICT_OF_THE_AGES_SERIES
    + (
        'Christian Service',
        'Christ’s Object Lessons',
        'Counsels on Stewardship',
        'The Ministry of Healing',
        'Steps to Christ',
        'The Story of Redemption',
        'Counsels on Diet and Foods',
        'The Great Controversy',
        'Life Sketches of Ellen G. White',
        ('Messages to Young People', 'MYP'),
        'Education',
        'Child Guidance',
        'The Adventist Home',
        'The Publishing Ministry',
        'Christ Our Saviour',
    ),
}
