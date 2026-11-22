# Bezbedan produkcioni release — SciConnect (#11)

Ovo je dodatak postojecem [vodicu za Hetzner](DEPLOYMENT.md).
Novi GitHub Actions workflow **Safe production release** nema push ili PR okidac.
Pokrece se samo rucno. Podrazumevano radi suvu proveru bez SSH pristupa,
bez registrija i bez produkcionih tajni.

## Preduslovi pre aktiviranja zivog deploy-a

1. Zavrsiti tiket **#9**: CI nad stvarnim PostgreSQL 17 i proba svih Alembic
   migracija od prazne baze. Postojeci SQLite testovi nisu zamena.
2. GitHub → Settings → Environments → **production**: ukljuciti required
   reviewers, ograniciti granu na main, po mogucnosti iskljuciti admin bypass
   i proveriti da odobrenje zaista blokira posao. **Workflow to ne moze da
   podesi ili potvrdi umesto vlasnika.**
3. U GitHub Environment production postaviti samo ove tajne:
   DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_PRIVATE_KEY, DEPLOY_SSH_KNOWN_HOSTS,
   GHCR_READ_USERNAME i GHCR_READ_TOKEN. SSH known_hosts mora biti proveren
   nezavisnim pouzdanim kanalom, ne automatski preuzet tokom release-a.
   GHCR token treba da ima samo read:packages i pristup odgovarajucim paketima.
   DB lozinka i APP_ADMIN_TOKEN ostaju samo na serveru u
   ~/SciConnect/.env.production (dozvole 600).
4. Postojeci Hetzner firewall treba da ostane restriktivan. GitHub-hostovani
   runneri imaju promenljive IP adrese: ne otvarati globalno port 22 samo da
   bi workflow mogao da pristupi serveru. Koristiti kontrolisani VPN,
   staticki egress ili namenski zastiteni deploy runner, uz odgovarajuce
   mreze/allowlist pravilo. U suprotnom zivi SSH korak nece raditi.
5. Na zasebnom staging serveru vezbati kopiju baze, migraciju, release,
   sve health/smoke provere i operator rollback. Proveriti slobodan disk.
6. Tek posle provere GitHub Environment pravila i staging vezbe dodati
   repository variable SCICONNECT_CD_ENABLED=true. Bez toga zivi deploy
   zavrsava neuspesno, ne preskace se tiho.

## Provera SHA i dry-run

Actions → Safe production release → Run workflow. Izabrati granu main,
puni SHA commita (40 malih heksadecimalnih znakova) i dry_run=true.

Pre svake objave proverava se:
- commit postoji i predak je origin/main;
- **bas taj SHA** ima zavrsen uspesan CI workflow, sa push dogadjajem na main;
- release skripte imaju ispravnu Bash sintaksu i unit testovi su zeleni;
- kombinovana produkciona Compose konfiguracija je validna.

Zelen PR CI nije dovoljan. Dry-run ne pravi GHCR slike, ne koristi SSH i
ne dodiruje produkciju. Novi workflow_dispatch fajl moze da ne bude vidljiv
u GitHub Actions interfejsu dok ne udje u default granu.

Za stvarni release potrebno je dry_run=false, eksplicitno odobrenje u
production Environment i ukljucena SCICONNECT_CD_ENABLED zastavica.
Aplikativne slike se grade iz testiranog SHA, objavljuju na GHCR i zatim
identifikuju iskljucivo nepromenljivim sha256 digestima. Tek tada pocinje
rad sa serverom. Sam merge u main **nikada** ne pokrece produkcioni deploy.

## Redosled zivog release-a

1. Proveriti SSH identitet i hash-pakovane slike. Ne menjati postojece
   produkcione lozinke ni portove.
2. Na serveru proveriti postojecu zdravu bazu, konfiguraciju i dostupnost
   novih slika. GitHub workflow i server koriste brave protiv preklapanja.
3. Napraviti custom-format PostgreSQL backup u
   ~/SciConnect/backups/pre-SHA-UTC.dump. Parcijalni dump nije prihvacen.
   Proveriti ga sa pg_restore --list i sacuvati SHA256 kontrolnu sumu.
   Potreban je i **odvojeni off-site backup**; kopija na istom hostu nije
   zastita od gubitka diska ili servera.
4. Pokrenuti jednokratnu Alembic migraciju iz nove pinovane slike, pre
   starta novog API-ja. APP_RUN_MIGRATIONS=false na release overlay-u
   sprecava automatsko pokretanje migracija pri restartu ili rollback-u.
   Postojeci rucni Compose bez overlay-a i dalje migrira pri startu.
5. Pustiti Compose sa --no-build --pull never --wait, nakon posebnog pull-a
   samo za pinovane API/frontend slike. Ovo sprecava neplanirani update
   promenljivih Postgres/Caddy tagova; potvrditi HTTPS
   pocetnu stranu, javni API health, katalog i interni SQL readiness
   sa migracionom revizijom.
6. Samo ako sve provere prodju snimiti release-state/current-release
   i release-state/previous-release sa SHA i tacnim image digestima.

Ako migracija ili smoke test ne prodju, workflow se oznacava kao neuspesan.
Skripta NE vraca automatski bazu: migracija je mozda vec promenila semu.
Lokacija backup-a i trag neuspeha ostaju, a vlasnik bira oporavak.

## Vezba restore-a bez produkcionih promena

Preneti poslednji custom .dump sa servera na staging/operatersku masinu.
Pokrenuti:

    bash scripts/release/restore_drill.sh /putanja/do/pre-release.dump

Skripta koristi NOVI privremeni PostgreSQL 17 kontejner bez portova i
volume-a, izvrsava pg_restore --exit-on-error i proverava postojanje
institutions tabele. Privremeni kontejner se uklanja i pri neuspehu.
Nije dozvoljen pristup produkcionoj bazi. Provera restore-a stvarnog
backup-a mora se zabeleziti pre ukljucivanja produkcionog CD-a.

**Nikada ne vracati dump direktno u postojecu produkcionu bazu.**
Za stvarni restore zaustaviti upise, sacuvati trenutno stanje, otvoriti
cistu ciljnu bazu i eksplicitno odobriti destruktivnu zamenu.
Ne postoji automatski Alembic downgrade.

## Rucni rollback aplikacije

Posle neuspesnog deploy-a poznato poslednje dobro izdanje nalazi se u
release-state/current-release. Nakon uspesnog izdanja koje se pokazalo
lose, prethodno dobro izdanje je previous-release. Skripta
scripts/release/remote_rollback.sh uzima izbor current ili previous,
ali **nikad ne vraca migracije baze**.

Pre pokretanja proveriti da stara aplikacija radi sa NOVOM semom i da su
stari GHCR digest-i jos dostupni. Potom kao deploy korisnik:

    cd ~/SciConnect
    CONFIRM_DB_COMPATIBLE=yes bash releases/ODGOVARAJUCI-SHA/scripts/release/remote_rollback.sh current

Ili izabrati previous za povratak na pretposlednju potvrdenu verziju.
Rollback skripta proverava javni HTTPS, API, katalog i DB readiness,
pa tek nakon tih provera oznacava vraceno izdanje kao poslednje dobro
(dok prethodni digest zadrzava za svesni roll-forward). Operator ipak
treba dodatno da proveri stvarne podatke i poslovne funkcije u browseru.
Ako migracija nije kompatibilna, potreban je zaseban plan oporavka baze.

**Prvi prelazak** sa rucno gradjene Docker slike nema sacuvan GHCR digest
te stare slike. Pre prvog odobrenog release-a sacuvati checkout, postojece
slike i testiran backup/restore plan (ili rucno uspostaviti pinovani
baseline). Bez toga nema garantovanog brzog rollback-a na staru verziju.

## Ogranicenja

- GitHub Environment prava, SSH pristup, prava za GHCR i firewall nisu
  automatski dokaziva ovim PR-om.
- Testiranje migracija na PostgreSQL iz tiketa #9 ostaje uslov za CD.
- Proba migracije i baze na stagingu je neophodna i ne zamenjuje je CI.
- Rollback aplikacije ne znaci rollback baze.
- Deploy nikada nije automatski posledica merge-a u main.
