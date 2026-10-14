COUNTIES = [
    "Harju", "Hiiu", "Ida-Viru", "Jõgeva", "Järva", "Lääne", "Lääne-Viru", "Põlva",
    "Pärnu", "Rapla", "Saare", "Tartu", "Valga", "Viljandi", "Võru",
]

CITIES = {
    "Tallinn": "1", "Tartu": "5", "Narva": "20", "Pärnu": "80", "Kohtla-Järve": "30", "Viljandi": "71",
    "Maardu": "74", "Rakvere": "44", "Kuressaare": "93", "Sillamäe": "40", "Võru": "65", "Valga": "68",
    "Jõhvi": "41", "Keila": "76", "Haapsalu": "90", "Paide": "72", "Saue": "76", "Elva": "61", "Tapa": "45",
    "Põlva": "63", "Türi": "72", "Rapla": "79", "Jõgeva": "48", "Kiviõli": "43", "Põltsamaa": "48",
    "Sindi": "86", "Paldiski": "76", "Kärdla": "92", "Kunda": "44", "Tõrva": "68", "Narva-Jõesuu": "29",
    "Kehra": "74", "Loksa": "74", "Otepää": "67", "Räpina": "64", "Tamsalu": "46", "Kilingi-Nõmme": "86",
    "Karksi-Nuia": "69", "Võhma": "70", "Antsla": "66", "Lihula": "90", "Mustvee": "49",
    "Suure-Jaani": "71", "Abja-Paluoja": "69", "Püssi": "43", "Mõisaküla": "69", "Kallaste": "60",
}

VALDS = [
    "Viimsi", "Harku", "Rae", "Saku", "Kiili", "Jõelähtme", "Anija", "Kuusalu", "Lääne-Harju", "Kose",
    "Raasiku", "Saue", "Tartu", "Kambja", "Luunja", "Nõo", "Kastre", "Peipsiääre", "Elva", "Kanepi",
    "Põlva", "Räpina", "Setomaa", "Rõuge", "Antsla", "Võru", "Otepää", "Tõrva", "Valga", "Mulgi",
    "Viljandi", "Põhja-Sakala", "Türi", "Järva", "Paide", "Rapla", "Kehtna", "Kohila", "Märjamaa",
    "Lääneranna", "Põhja-Pärnumaa", "Tori", "Saarde", "Häädemeeste", "Kihnu", "Saaremaa", "Muhu",
    "Ruhnu", "Hiiumaa", "Haapsalu", "Lääne-Nigula", "Vormsi", "Tapa", "Kadrina", "Haljala", "Vinni",
    "Väike-Maarja", "Rakvere", "Viru-Nigula", "Alutaguse", "Toila", "Lüganuse", "Jõgeva", "Mustvee",
]

VILLAGES = [
    "Peetri", "Pärnamäe", "Tabasalu", "Muraste", "Haabneeme", "Laagri", "Jüri", "Vääna", "Tammneeme",
    "Püünsi", "Lagedi", "Uuesalu", "Kurna", "Assaku", "Lehmja", "Vaida", "Tõrvandi", "Ülenurme",
    "Haage", "Vahi", "Raadi-Kruusamäe", "Kõrveküla", "Lohkva", "Tõravere", "Kambja", "Melliste",
    "Kõrve", "Kanepi", "Mooste", "Sõmerpalu", "Puhja", "Rõngu", "Kärkna", "Paikuse", "Uulu",
]

TALLINN_DISTRICTS = ["Kesklinna", "Lasnamäe", "Mustamäe", "Nõmme", "Pirita", "Põhja-Tallinna", "Haabersti", "Kristiine"]

STREET_STEMS = [
    "Tamme", "Kase", "Kuuse", "Männi", "Pärna", "Vahtra", "Lepa", "Pihlaka", "Kastani", "Aia", "Pargi",
    "Kooli", "Jaama", "Posti", "Turu", "Sadama", "Mere", "Ranna", "Metsa", "Välja", "Nurme", "Niidu",
    "Põllu", "Karja", "Lossi", "Kiriku", "Tööstuse", "Vabriku", "Raua", "Liivalaia", "Majaka", "Pae",
    "Ümera", "Vikerlase", "Kotka", "Kalda", "Riia", "Raatuse", "Ülikooli", "Rüütli", "Vanemuise",
    "Kalevi", "Lille", "Aasa", "Kesk", "Uus", "Vana", "Pikk", "Lai", "Lühike", "Väike", "Suur",
    "Tuukri", "Telliskivi", "Kopli", "Sitsi", "Rahu", "Rõõmu", "Sõbra", "Tähe", "Kaunase", "Akadeemia",
    "Ehitajate", "Kadaka", "Laagna", "Mustamäe", "Linnu", "Sõpruse", "Vabaduse", "Pirita", "Kadrioru",
    "Narva", "Pärnu", "Tartu", "Peterburi", "Paldiski", "Viljandi", "Rakvere", "Jõe", "Kraavi",
    "Oja", "Allika", "Mäe", "Oru", "Lõuna", "Põhja", "Ida", "Lääne", "Kevade", "Suve", "Sügise",
    "Talve", "Õie", "Marja", "Vaba", "Rahumäe", "Kännu", "Mõisa", "Veski", "Kalmistu", "Spordi",
]

STREET_TYPES = [
    ("tänav", "tn", 0.62), ("maantee", "mnt", 0.08), ("puiestee", "pst", 0.06), ("tee", "tee", 0.14),
    ("põik", "põik", 0.05), ("allee", "allee", 0.02), ("väljak", "väljak", 0.03),
]

FARM_STEMS = ["Mäe", "Kase", "Tamme", "Jaani", "Uue", "Vana", "Metsa", "Allika", "Kivi", "Oja", "Pihlaka", "Sepa", "Tõnise", "Hansu", "Andrese", "Mardi", "Pärtli", "Jüri", "Kaasiku", "Nõmme"]

AGENCIES = [
    "Töötukassa", "Sotsiaalkindlustusamet", "Maksu- ja Tolliamet", "Politsei- ja Piirivalveamet",
    "Tervisekassa", "Transpordiamet", "Rahvastikuregister", "Riigi Infosüsteemi Amet", "Kohtutäitur",
    "Tallinna Linnavalitsus", "Tartu Linnavalitsus", "valla sotsiaalosakond", "Haridus- ja Noorteamet",
    "Keskkonnaamet", "Päästeamet", "Maa- ja Ruumiamet", "Ettevõtluse ja Innovatsiooni Sihtasutus",
]

AGENCIES_RU = ["Кассу по безработице", "Департамент социального страхования", "Налогово-таможенный департамент", "Департамент полиции и погранохраны", "Больничную кассу"]

CITIES_RU = {
    "Tallinn": "Таллинн", "Tartu": "Тарту", "Narva": "Нарва", "Pärnu": "Пярну", "Kohtla-Järve": "Кохтла-Ярве",
    "Sillamäe": "Силламяэ", "Jõhvi": "Йыхви", "Maardu": "Маарду", "Narva-Jõesuu": "Нарва-Йыэсуу", "Kiviõli": "Кивиыли",
}

ID_DOC_PREFIXES = [
    "AA", "AB", "AC", "AD", "BD", "BE", "BF", "CD", "CF", "EA", "EB", "EC", "ED", "FB", "FC", "FD", "FE", "FF",
    "KD", "KE", "KF", "KG", "MD", "ME", "MF", "MG", "NA", "PB", "PC", "PE", "PF", "RD", "RE", "RF", "SD",
    "SE", "SF", "SG", "UA", "UB", "VD", "VE", "VF", "VG",
]

BANK_CODES = ["22", "10", "77", "17", "96", "42", "33", "75", "12"]

EMAIL_DOMAINS = [("gmail.com", 40), ("mail.ee", 14), ("hot.ee", 8), ("eesti.ee", 6), ("online.ee", 3), ("outlook.com", 8), ("hotmail.com", 5), ("yahoo.com", 3), ("mail.ru", 5), ("inbox.lv", 2), ("icloud.com", 4), ("neti.ee", 2)]
