# Postman integraciniai testai KAN-9 ir KAN-10

Šiame dokumente pateikti 2 integraciniai testai su Postman. Kiekvienas testas turi po 2 testinius atvejus, kad būtų padengtas funkcionalumas ir nefunkciniai reikalavimai.

## Bendros pastabos

- Visi request'ai siunčiami į jau paleistą aplikaciją.
- Jei endpoint'as yra apsaugotas autentifikacija, Postman turi turėti sesijos slapukus arba prisijungimo užklausą prieš testus.
- Testuose galima naudoti `pm.response.to.have.status(...)`, `pm.expect(...)` ir atsakymo JSON tikrinimą.

---

## 1 testas: KAN-9 - sistema informuoja, jeigu paieškos metu nebuvo rastų rezultatų

### Tikslas
Patikrinti, ar paieškos API aiškiai grąžina informaciją apie tuščius rezultatus ir ar teigiamu atveju grąžina rastus produktus.

### Susiję komponentai
- API sluoksnis: `/api/search/`
- Paieškos logika: `search_products`, `has_search_results`
- JSON atsakymas klientui

### Precondition
- Aplikacija paleista.
- DB turi produktų duomenų.

### TA1: Paieška neranda rezultatų
**Request**
- Method: `GET`
- URL: `/api/search/?q=neegzistuojantisproduktas123`

**Expected**
- Status code: `200`
- `results` yra tuščias masyvas
- `no_results` yra `true`
- `query` atsakyme sutampa su perduota reikšme

**Postman testų pavyzdys**
```javascript
pm.test('Status code is 200', function () {
  pm.response.to.have.status(200);
});

const json = pm.response.json();
pm.test('No results is true', function () {
  pm.expect(json.no_results).to.eql(true);
});

pm.test('Results is empty', function () {
  pm.expect(json.results).to.be.an('array').that.is.empty;
});
```

### TA2: Paieška randa rezultatus
**Request**
- Method: `GET`
- URL: `/api/search/?q=pienas`

**Expected**
- Status code: `200`
- `results` masyvas nėra tuščias, jei DB yra toks produktas
- `no_results` yra `false`
- Kiekvienas rezultatas turi bent `name` ir `rep_id`

**Postman testų pavyzdys**
```javascript
pm.test('Status code is 200', function () {
  pm.response.to.have.status(200);
});

const json = pm.response.json();
pm.test('Results are returned', function () {
  pm.expect(json.results).to.be.an('array');
  pm.expect(json.results.length).to.be.greaterThan(0);
});

pm.test('No results is false', function () {
  pm.expect(json.no_results).to.eql(false);
});
```

### Nefunkciniai patikrinimai
- Atsakymas turi būti JSON formato.
- Tuščios paieškos atvejis neturi kelti serverio klaidos.
- Atsakymo schema turi būti stabili: `query`, `category`, `selected_filters`, `results`, `no_results`.

---

## 2 testas: KAN-10 - sistema pateikia palygintus krepšelius su kainom

### Tikslas
Patikrinti, ar kainų palyginimo funkcija grąžina teisingą palyginimo rezultatą ir ar API teisingai veikia tiek su turimais duomenimis, tiek su ribiniais atvejais.

### Susiję komponentai
- API sluoksnis: `/template/<int:template_id>/compare/`
- Verslo logika: `compare_template_prices`
- Duomenų bazė: `BasketTemplate`, `BasketTemplateItem`, `Product`
- JSON atsakymas klientui

### Precondition
- Yra sukurtas šablonas su bent 1–2 produktais.
- DB turi produktus iš kelių parduotuvių, kad būtų galima apskaičiuoti kainų palyginimą.

### TA1: Palyginti esamą šabloną su kainomis
**Request**
- Method: `GET`
- URL: `/template/1/compare/`

**Expected**
- Status code: `200`
- Atsakymas yra JSON
- Atsakyme yra `items`
- Atsakyme yra `totals`
- Atsakyme yra `cheapest_store`
- Kainos palyginimas grąžina duomenis apie bent vieną parduotuvę

**Postman testų pavyzdys**
```javascript
pm.test('Status code is 200', function () {
  pm.response.to.have.status(200);
});

const json = pm.response.json();
pm.test('Comparison response has required keys', function () {
  pm.expect(json).to.have.property('items');
  pm.expect(json).to.have.property('totals');
  pm.expect(json).to.have.property('cheapest_store');
});

pm.test('Items array is not empty', function () {
  pm.expect(json.items).to.be.an('array');
  pm.expect(json.items.length).to.be.greaterThan(0);
});
```

### TA2: Bandymas palyginti neegzistuojantį šabloną
**Request**
- Method: `GET`
- URL: `/template/99999/compare/`

**Expected**
- Status code: `200` arba klaida pagal `compare_template_prices` elgseną, bet atsakymas neturi sugadinti kliento pusės
- Jei funkcija grąžina klaidos JSON, jame turi būti aiškus `error`
- Sistema neturi nulūžti

**Postman testų pavyzdys**
```javascript
pm.test('Response is received', function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 400, 404]);
});

const json = pm.response.json();
pm.test('Response contains either comparison data or error', function () {
  pm.expect(json).to.satisfy(function (value) {
    return value.error || value.items || value.totals || value.cheapest_store;
  });
});
```

### Nefunkciniai patikrinimai
- Palyginimo atsakymas turi būti JSON formato.
- Skaičiavimai turi būti stabilūs ir pakartojami su tais pačiais duomenimis.
- Sistema turi apdoroti ir ribinius atvejus be serverio crash.

---

## Rekomenduojama Postman kolekcijos struktūra

- Folder: `KAN-9 Search`
  - Request: `Search no results`
  - Request: `Search with results`
- Folder: `KAN-10 Compare`
  - Request: `Compare existing template`
  - Request: `Compare non-existing template`

Jei nori, galiu dar paruošti ir pilną Postman collection turinį su konkrečiais URL, environment variables ir `Tests` skriptais, kad galėtum tiesiog importuoti į Postman.
