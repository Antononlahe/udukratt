# Udukratt showcase

Seven hard, fully fabricated inputs, with Udukratt v0.1 output and Bürokratt Presidio-Anonymizer output for contrast. Wins and failures are both shown. See [BENCHMARKS.md](BENCHMARKS.md) for the numbers.

## Code-switching chat (et/ru/en)

Input:
```
привет, kas sa saatsid selle arve juba? Михаил Петров ütles, et IBAN EE382200221020145685 on vale. pls check w/ tiina kask asap, her phone +372 5123 4567. спасибо!
```
Udukratt:
```
привет, kas sa saatsid selle arve juba? [GIVEN_NAME] [SURNAME] ütles, et IBAN [BANK_ACCOUNT] on vale. pls check w/ [GIVEN_NAME] [SURNAME] [SURNAME], her phone [PHONE]. спасибо!
```
Bürokratt:
```
привет, kas sa saatsid selle arve juba? [ISIK] ütles, et IBAN [PANGAKONTO] on vale. pls check w/ [ISIK] asap, her phone [TELEFON]. спасибо!
```
Both catch the IBAN and phone. Udukratt also redacts the trailing 'asap' as a surname, while Bürokratt keeps it.

## Confluence/XML blob

Input:
```
<ac:structured-macro ac:name="info"><ac:rich-text-body><p>Klient: <strong>Jaanus Tamm</strong> (isikukood 38001085718)</p><table><tr><td>IBAN</td><td>EE471000001020145685</td></tr><tr><td>page-id</td><td>a3f1c2e9-4b7d-4e2a-9c1f-0d5e6b7a8c9f</td></tr></table></ac:rich-text-body></ac:structured-macro>
```
Udukratt:
```
<ac:structured-macro ac:name="info"><ac:[GIVEN_NAME]><p>Klient: <strong>[GIVEN_NAME] [SURNAME]</strong> (isikukood [ISIKUKOOD])</p><table><tr><td>IBAN</td><td>[BANK_ACCOUNT]</td></tr><tr><td>page-id</td><td>a3f1c2e9-4b7d-4e2a-9c1f-0d5e6b7a8c9f</td></tr></table></ac:[SURNAME]-[SURNAME]></ac:structured-macro>
```
Bürokratt:
```
<ac:structured-macro ac:name="info"><ac:rich-text-body><p>Klient: <strong>Jaanus [ISIK]> (isikukood [ISIKUKOOD])</p><table><tr><td>IBAN</td><td>[PANGAKONTO]</td></tr><tr><td>page-id</td><td>a3f1c2e9-4b7d-4e2a-9c1f-0d5e6b7a8c9f</td></tr></table></ac:rich-text-body></ac:structured-macro>
```
Both keep the UUID. Udukratt wrongly tags XML tag names (`rich-text-body`). Bürokratt leaves 'Jaanus' unredacted and eats the `</strong` tag.

## YAML payload inside an email

Input:
```
From: support@naidis-pood.ee
Subject: Re: tellimus JIRA-4821

Tere, allpool andmed:

```yaml
customer:
  name: Kadri Lepik
  id_code: 49403136526
  email: kadri.lepik@example.ee
  address: Pärnu mnt 15-7, Tallinn
order_ref: ORD-2026-000917
build: v2.14.3
```
Parimate soovidega,
Mart
```
Udukratt:
```
From: [EMAIL]
Subject: Re: [STREET_NAME] [SURNAME]-4821

Tere, allpool andmed:

```yaml
customer:
  name: [GIVEN_NAME] [SURNAME]
  id_code: [ISIKUKOOD]
  email: [EMAIL]
  address: [STREET_NAME] [BUILDING_NUMBER]-[SECONDARY_ADDRESS], [CITY]
order_ref: ORD-2026-000917
build: v2.14.3
```
[GIVEN_NAME] [SURNAME],
[GIVEN_NAME]
```
Bürokratt:
```
From: [E-POST]
Subject: Re: tellimus JIRA-4821

Tere, allpool andmed:

```yaml
customer:
  name: [ISIK]
  id_code: [ISIKUKOOD]
  email: [E-POST]
  address: [ASUKOHT], [GPE]
[GPE]: ORD-2026-000917
build: v2.14.3
```
Parimate soovidega,
Mart
```
Udukratt redacts the address in full, but it tags the ticket subject and the sign-off. Bürokratt redacts `order_ref` as a place and misses 'Mart'.

## OCR noise

Input:
```
AVALDUS
Nimi: Rein0 Saarna
Isikuk0od: 3900l2l0274
Aadress : Tartu mnt 4l, Tal1inn
Tel. 5l2 34567
Kuupäev 12.O3.2026
```
Udukratt:
```
AVALDUS
Nimi: [GIVEN_NAME] [SURNAME]
Isikuk0od: [GOVERNMENT_ID]
Aadress : [STREET_NAME] [BUILDING_NUMBER], [CITY]
Tel. [PHONE]
Kuupäev 12.O3.2026
```
Bürokratt:
```
AVALDUS
Nimi: [ISIK]
[ISIK]: 3900l2l0274
Aadress : [ASUKOHT], [GPE]
[GPE]. 5l2 34567
Kuupäev 12.O3.2026
```
Udukratt survives the OCR noise (l→1, O→0) for both the id and the phone. Bürokratt leaves both readable.

## Lowercase names + look-alike ids

Input:
```
ticket SUP-10233 avas peeter mägi, commit 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b, uuid 550e8400-e29b-41d4-a716-446655440000. peeter mägi palus helistada ka liisa oksale.
```
Udukratt:
```
ticket SUP-10233 avas [GIVEN_NAME] [SURNAME], commit 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b, uuid 550e8400-e29b-41d4-a716-446655440000. peeter [SURNAME] palus helistada ka [GIVEN_NAME] [SURNAME].
```
Bürokratt:
```
ticket [ORGANISATSIOON] avas [ASUKOHT], commit 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b, uuid 550e8400-e29b-41d4-a716-446655440000. [ASUKOHT] palus [GPE] ka liisa oksale.
```
Udukratt keeps the ticket, hash and UUID and catches the lowercase names, but misses 'peeter' once. Bürokratt tags the ticket as an organisation and leaves 'liisa oksale' unredacted.

## Surname-only references

Input:
```
Koosolekul olid Kask, Tamm ja Õunapuu. Kask lubas Tammele saata lepingu, Õunapuu vastutab eelarve eest. Hr Kuusk puudus.
```
Udukratt:
```
Koosolekul olid Kask, Tamm ja Õunapuu. Kask lubas Tammele saata lepingu, Õunapuu vastutab eelarve eest. Hr Kuusk puudus.
```
Bürokratt:
```
Koosolekul olid Kask, Tamm ja [ISIK]. Kask lubas [ISIK] saata lepingu, [ISIK] vastutab eelarve eest. Hr [ISIK] puudus.
```
Bürokratt catches surname-only references that Udukratt misses entirely. This is a real Udukratt weakness.

## Russian name in Estonian text with ID document

Input:
```
Taotleja Ольга Смирнова (Olga Smirnova), dokumendi nr AB0123456, sünd 1985, elukoht Narva, Kreenholmi 12-3. Kontakt olga.smirnova@mail.ee.
```
Udukratt:
```
Taotleja [GIVEN_NAME] [SURNAME] ([GIVEN_NAME] [SURNAME]), dokumendi nr [GOVERNMENT_ID], sünd [SECONDARY_ADDRESS], elukoht [CITY], [SURNAME] [BUILDING_NUMBER]-[SECONDARY_ADDRESS]. Kontakt [EMAIL].
```
Bürokratt:
```
Taotleja [ISIK] (Olga [ISIK]), dokumendi nr [EST-DOKUMENDINR], sünd 1985, elukoht [GPE], [ASUKOHT]. Kontakt [E-POST].
```
Both catch the Cyrillic name and the document number. Udukratt splits the address oddly and tags the birth year. Bürokratt misses 'Olga'.
