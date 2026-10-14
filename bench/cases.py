CASES = [
("Code-switching chat (et/ru/en)", "привет, kas sa saatsid selle arve juba? Михаил Петров ütles, et IBAN EE382200221020145685 on vale. pls check w/ tiina kask asap, her phone +372 5123 4567. спасибо!"),
("Confluence/XML blob", '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>Klient: <strong>Jaanus Tamm</strong> (isikukood 38001085718)</p><table><tr><td>IBAN</td><td>EE471000001020145685</td></tr><tr><td>page-id</td><td>a3f1c2e9-4b7d-4e2a-9c1f-0d5e6b7a8c9f</td></tr></table></ac:rich-text-body></ac:structured-macro>'),
("YAML payload inside an email", "From: support@naidis-pood.ee\nSubject: Re: tellimus JIRA-4821\n\nTere, allpool andmed:\n\n```yaml\ncustomer:\n  name: Kadri Lepik\n  id_code: 49403136526\n  email: kadri.lepik@example.ee\n  address: Pärnu mnt 15-7, Tallinn\norder_ref: ORD-2026-000917\nbuild: v2.14.3\n```\nParimate soovidega,\nMart"),
("OCR noise", "AVALDUS\nNimi: Rein0 Saarna\nIsikuk0od: 3900l2l0274\nAadress : Tartu mnt 4l, Tal1inn\nTel. 5l2 34567\nKuupäev 12.O3.2026"),
("Lowercase names + look-alike ids", "ticket SUP-10233 avas peeter mägi, commit 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b, uuid 550e8400-e29b-41d4-a716-446655440000. peeter mägi palus helistada ka liisa oksale."),
("Surname-only references", "Koosolekul olid Kask, Tamm ja Õunapuu. Kask lubas Tammele saata lepingu, Õunapuu vastutab eelarve eest. Hr Kuusk puudus."),
("Russian name in Estonian text with ID document", "Taotleja Ольга Смирнова (Olga Smirnova), dokumendi nr AB0123456, sünd 1985, elukoht Narva, Kreenholmi 12-3. Kontakt olga.smirnova@mail.ee."),
]
