# Eesti keele reeglid tehnilises dokumentatsioonis

## Üldised kirjutamisreeglid

### Suurtähtede kasutamine

- **Ainult esimene sõna ja pärisnimed** suure tähega
- **Vale**: "Tehnilise Võla Vähendamine", "Git Repository"
- **Õige**: "Tehnilise võla vähendamine", "Git repositoorium"

### Pealkirjade vormistamine

```markdown
## 1. Git repositooriumite nõuetekohaseks viimine
### Ülesanded vastavalt juhendile
```

## Ingliskeelsete terminite käsitlemine

### 1. Tõlgi eesti keelde, kui hea vaste on olemas

- **"security issues"** → **"turvaprobleemid"**
- **"performance issues"** → **"jõudlusprobleemid"**
- **"code quality"** → **"koodi kvaliteet"**
- **"user stories"** → **"kasutuslood"**
- **"user journeys"** → **"kasutajateed"**

### 2. Säilita laialt kasutatavad tehnilised terminid

Järgmised terminid on eesti IT-s üldiselt vastu võetud:

- **API** (Application Programming Interface)
- **CI/CD** (Continuous Integration/Continuous Deployment)
- **Docker**
- **Git**
- **JSON**
- **pipeline** (eriti CI/CD kontekstis)
- **repository** (võib ka "repositoorium")
- Programmeerimiskeeled: **Java**, **.NET**, **Node.js**
- Andmebaasid: **Redis**, **RabbitMQ**, **PostgreSQL**
- Testimisraamistikud: **Selenium**, **Playwright**, **Cypress**

### 3. Kasuta jutumärke uuemate või vähem tuttavate terminite jaoks

- **"Infrastructure as Code"**
- **"semantic versioning"**
- **"circuit breaker pattern"**
- **"strangler fig pattern"**
- **"container'id"** - ingliskeelsed terminid eesti käänetes (välja arvatud pipeline)
- **"code review"**, **"refaktooringud"**, **"deployment"**
- **"critical"**, **"high severity"**, **"code smells"**
- **"New Code"**, **"test coverage"**, **"unit testid"**
- **"security vulnerabilities"**, **"dependencies"**
- **"user journeys"**, **"automation tools"**, **"End-to-end"**

### 4. Eesti vastete eelistamine

- **"inventory"** → **"kaardistada"** (mitte "inventariseerida")
- **"implement"** → **"implementeerida"** või **"rakendada"**
- **"deploy"** → **"rakendada"** või **"käiku lasta"**
- **"best practices"** → **"parimad tavad"**
- **"issues"** → **"probleemid"** või **-vigad**
- **"performance"** → **"jõudlus"**
- **"security"** → **"turvalisus"** või **"turva-"**

### 5. Hübriidterminid (pool-inglise, pool-eesti)

- **"smoke testid"** - aktsepteeritav, kui ingliskeelne osa on jutumärkides
- **"regression testid"** - aktsepteeritav
- **API "versioning"** - eelistada, kui eesti vaste on keeruline

## Ülesannete vormistamine

### Numeratsiooni süsteem

Kasuta jaotuse numbril põhinevat numeratsiooni:

```markdown
## 1. Git repositooriumite seadistamine
1.1. Auditeerida kõik repositooriumid

1.2. Luua README failid

1.3. Seadistada CI/CD

## 2. Versioonihaldus
2.1. Kokku leppida reeglid

2.2. Implementeerida SemVer
```

### Confluence vormindamise nõuded

**KRIITILINE**: Confluence vajab spetsiaalset vormindamist:

#### 1. Tühjad read numbrite vahel

```markdown
1.1. Esimene ülesanne

1.2. Teine ülesanne

1.3. Kolmas ülesanne

## 9. Järgmine suur jaotus

```

Ilma õigete ridadeta muutub dokument Confluence'is loetamatuks.

### Ülesannete sõnastamine

- **Alusta tegevussõnaga**: "Auditeerida", "Implementeerida", "Seadistada"
- **Ole konkreetne**: "Implementeerida semantic versioning (SemVer)" vs "Parandada versiooniprobleemid"
- **Sisalda tegelikku tööd**: Ära piirdu ainult planeerimise ja kaardistamisega

## Viidete vormistamine

### Wiki viited

Lingi tekst (wiki lehe pealkiri) pane jutumärkidesse:

```markdown
### Ülesanded vastavalt ["Tehnilistele nõuetele"](https://example.internal)
```

### Mitme viite puhul

```markdown
### Ülesanded vastavalt ["Tehnilistele nõuetele"](link1) ja ["Tehnoloogiakaardile"](link2)
```

### Näidete lisamine

```markdown
4.5. **Java näide:** ["Bookstore Boot Backend"](https://example.internal)
```

**Põhjendus**: Kuna tsiteerime wiki lehekülgede pealkirju, on jutumärgid sobivad.

## Tehnilised soovitused

### Akronüümide selgitamine

Esimesel kasutamisel:

```markdown
- Seadistada CI/CD (Continuous Integration/Continuous Deployment)
- Rakendada API (Application Programming Interface) standardid
```

### Versiooninumbrite vormistamine

```markdown
- Java 17
- .NET 8
- Node.js 18
```

### Tehnoloogiate loetlemine

```markdown
- Programmeerimiskeeled (Java, .NET, Node.js jne)
- Platvormteenused (Redis, RabbitMQ, PostgreSQL jne)
```

## Stiili soovitused

### Lause pikkus

- Hoia laused lühikesed ja arusaadavad
- Ühes lauses üks peamõte
- Väldi liialt keerulisi lausestruktuure

### Passiivis vs aktiivses kõnes

- **Eelistatud**: "Meeskond implementeerib API standardid"
- **Väldi**: "API standardid implementeeritakse"

### Tuleviku väljendamine

- **"tuleb"**: kohustuslik tegevus ("tuleb implementeerida")
- **"võiks"**: soovituslik tegevus ("võiks lisada")
- **"peab"**: range nõue ("peab vastama standardile")

## Ülesannete prioritiseerimine

### Selged toimingud

- **Audit/analüüs**: "Auditeerida", "Kaardistada", "Analüüsida"
- **Planeerimine**: "Planeerida", "Prioritiseerida", "Valida"
- **Implementeerimine**: "Implementeerida", "Rakendada", "Seadistada"
- **Testimine**: "Testida", "Valideerida", "Kontrollida"

### Täpsustused sulgudes

```markdown
2.3. Implementeerida "semantic versioning" (SemVer)
4.2. Implementeerida struktureeritud logimine (JSON "format")
5.2. Valida sobivad "automation tools" (Selenium, Playwright, Cypress jne)
```

### Ajaformaadid ja tähtajad

```markdown
- **Q1 2024** - kvartalite tähistamine
- **jaanuar-märts 2024** - kuude vahemik
- **1-2 nädalat** - ajaline hinnang
```

## Välditavad vead

### Ülemäärane inglise keele kasutamine

- **Vale**: "Implementeerida best practices"
- **Õige**: "Rakendada parimad tavad"

### Ebaselged ülesanded

- **Vale**: "Parandada probleemid"
- **Õige**: "Parandada Sonar poolt tuvastatud code smells"

### Liiga üldised väljendid

- **Vale**: "Teha vajalikke muudatusi"
- **Õige**: "Uuendada "vulnerable dependencies""

### Vastuolulised terminid

- **Vale**: Sama termin kord jutumärkides, kord ilma
- **Õige**: Järjepidev kasutamine kogu dokumendis
- **Näide**: Kas "container'id" või container'id - vali üks ja kasuta järjepidevalt

## Kokkuvõte

1. **Kasuta õiget eesti keele õigekirja** - ainult esimene sõna ja pärisnimed suure tähega
2. **Tõlgi, kui hea vaste olemas** - eelistada eesti keelt seal, kus võimalik
3. **Säilita tuntud tehnilised terminid** - API, CI/CD, Docker, Java jne (ilma jutumärkideta)
4. **Pane jutumärgid uute terminite ümber** - "container'id", "code review", "deployment"
5. **Ole järjepidev terminite kasutamisel** - sama termin alati samamoodi
6. **Ole konkreetne ülesannetega** - sisalda tegelikku implementeerimistööd
7. **Kasuta selget numeratsiooni** - iga jaotus oma numbriga
8. **Lisa viited ja näited** - aita meeskondi praktiliste linkidega

## Kiire kontroll-loend

Enne dokumendi avaldamist kontrolli:

- [ ] Ainult esimene sõna ja pärisnimed suure tähega
- [ ] Ingliskeelsed terminid kas tõlgitud või jutumärkides
- [ ] Järjepidev terminikasutus kogu dokumendis
- [ ] Konkreetsed tegevused, mitte üldised soovitused
- [ ] Viited wiki lehekülgedele ja näidetele
- [ ] Selge numeratsioon ja struktuur
- [ ] Tühjad read iga numbri vahel (Confluence nõue)
