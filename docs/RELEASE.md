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
   i proveriti da odobrenje zaista blokira posao. **Obavezno** ograniciti
   produkcioni Environment na main (pravilo grana), zahtevati zasebnog
   reviewera i zabraniti sopstveno odobravanje gde plan dozvoljava.
   **Workflow to ne moze da
   podesi ili potvrdi umesto vlasnika.**
3. U GitHub Environment production postaviti samo ove tajne:
   DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_PRIVATE_KEY, DEPLOY_SSH_KNOWN_HOSTS,
   GHCR_READ_USERNAME i GHCR_READ_TOKEN. SSH known_hosts mora biti proveren
   nezavisnim pouzdanim kanalom, ne automatski preuzet tokom release-a.
   GHCR token treba da ima samo read:packages i pristup odgovarajucim paketima.
   GitHub server moze imati sistemski Docker credential helper (`pass`
   ili `secretservice`) koji bi token sacuvao izvan privremenog foldera.
   Launcher zato posle login-a **zahteva** `auths.ghcr.io.auth` u
   privremenom config.json, bez `credsStore`/`credHelpers`; inace
   pokusava `docker logout` i odbija release. Ovo proveriti i na staging
   hostu sa stvarnom konfiguracijom, bez zapisivanja tokena u log.
   Token se tokom release-a cuva samo u privremenom server-side
   DOCKER_CONFIG direktorijumu, koji se po zavrsetku pozadinskog
   release procesa brise. Prekinut proces bez zavrsnog statusa zahteva
   da operator ukloni zaostali token i rotira ga, ako postoji sumnja na
   kompromitovanje.
   DB lozinka i APP_ADMIN_TOKEN ostaju samo na serveru u
   ~/SciConnect/.env.production (dozvole 600).
4. Postojeci Hetzner firewall treba da ostane restriktivan. GitHub-hostovani
   runneri imaju promenljive IP adrese: ne otvarati globalno port 22 samo da
   bi workflow mogao da pristupi serveru. Koristiti kontrolisani VPN,
   staticki egress ili namenski zastiteni deploy runner, uz odgovarajuce
   mreze/allowlist pravilo. U suprotnom zivi SSH korak nece raditi.
5. Na zasebnom staging serveru vezbati kopiju baze, migraciju, release,
   sve health/smoke provere i operator rollback. Proveriti slobodan disk.
   Proveriti aktivni systemd-logind policy preko
   `busctl get-property org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager KillUserProcesses`
   i `KillOnlyUsers`. Pre starta skripta zahteva stvarno `b false`
   i da korisnik deploy nije u KillOnlyUsers; ne oslanja se na fajl koji
   mozda nije ucitan ni na distro podrazumevane vrednosti. Ako se vrednosti
   ne mogu procitati ili su opasne, release se **odbija**. Posebna
   per-user pravila ili prilagodjeni logind setup zahtevaju zasebnu
   staging proveru stvarnog SSH prekida.
   Staging proba mora da ukljuci prekid SSH veze tokom migracije.
   Proveriti i Compose pod privremenim Docker configom
   (`DOCKER_CONFIG="$(mktemp -d)" docker compose version`).
   Odobravalac mora eksplicitno
   potvrditi da prethodni off-site backup postoji i da je odradjena proba
   vracanja baze na stagingu; workflow ne moze sam dokazati ove uslove.
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
- kombinovana produkciona Compose konfiguracija **iz izabranog SHA**
  je validna (a ne samo trenutna verzija main grane).

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
   Proveriti citav dump sa pg_restore -f /dev/null (ne samo TOC sa --list)
   i sacuvati SHA256 kontrolnu sumu. Ovo nije zamena za vezbu stvarnog restore-a.
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
   Ponovni build ISTOG commita moze napraviti drugacije digest-e; prethodna
   poznato-dobra verzija se cuva kad se razlikuje SHA ili bilo koji digest.
   Server-side zapis o pokusaju cuva se u
   ~/SciConnect/release-state/deploy-attempts/RUN_ID-ATTEMPT/
   (release.log, exit-code, worker.pid). Skripta prijavljuje RELEASE_OK
   samo ako je backend stvarno zavrsio i sve provere prosle.

**Prekid workflow-a nije prekid deploymenta.** Nakon sto je release proces
pokrenut na serveru nezavisno od SSH sesije, otkazivanje GitHub Actions
posla ili privremeni prekid mreze NE zaustavlja migraciju. Ne pokretati
novi deploy napamet: prvo proveriti server-side log i exit-code, stanje
baze, postojeci release-state/current-release i zdravlje sajta.
Dok je proces u toku, server-side flock sprecava paralelan rollout.
Status RELEASE_UNKNOWN je incident za operatersku istragu, ne dozvola
za automatsko ponavljanje. Nadzor koristi deadline od 85 minuta,
a job timeout 120 minuta. Ako je mnogo sporiji backup ili migracija,
GitHub job moze zavrsiti neuspesno dok server nastavlja posao; operater
prvo proverava server-side status.
U slucaju SIGKILL/OOM/reboot kada worker ne izvrsi trap, token ostaje u
starom docker-auth direktorijumu; novi start automatski cisti stale
direktorijume starije od 24 sata samo ako vise nema zivog worker PID-a.
U hitnom incidentu token rucno rotirati i proveriti disk.

Ako migracija ili smoke test ne prodju, workflow se oznacava kao neuspesan.
Skripta NE vraca automatski bazu: migracija je mozda vec promenila semu.
Lokacija backup-a i trag neuspeha ostaju, a vlasnik bira oporavak.

**Disk/retention:** pre backup-a proverava se raspoloziv prostor
(najmanje dvostruka velicina baze plus 512 MiB rezerve). Backup i izdanja
se **ne brisu automatski**: operator mora redovno da proverava kapacitet,
odnosi proverene kopije van servera i zatim rucno uklanja stare dump-ove.
Ne brisati poslednje proverene off-site kopije niti release direktorijume
za current/previous: Caddy koristi fajl iz aktivnog direktorijuma.

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

## Promena konfiguracije i rotacija admin kljuca

Nakon prvog pinovanog release-a **ne pokretati** legacy `docker compose
up -d api` bez odgovarajuceg release overlay-a. Za promenu
`APP_ADMIN_TOKEN` (ukljucujuci hitnu rotaciju kompromitovanog kljuca),
rate limita i drugih parametara:

1. Kao deploy korisnik proveriti i urediti
   `~/SciConnect/.env.production` uz dozvole 600; vrednosti ne upisivati u
   GitHub komentare ili logove. Sacuvati rezervnu kopiju konfiguracije
   na bezbednom mestu.
2. Ponovo primeniti **current** pinovanu verziju, bez migriranja baze:

       cd ~/SciConnect
       sha="$(awk '{print $1}' release-state/current-release)"
       CONFIRM_DB_COMPATIBLE=yes bash "releases/$sha/scripts/release/remote_rollback.sh" current

   Ova skripta koristi istu Compose overlay datoteku i pinovane digest-e.
   Ako su oba digest-a lokalno sacuvana, povratak ne zavisi od GHCR.
   Promena env postavki treba da izazove Compose recreate odgovarajuceg
   kontejnera; proveriti status i, za admin token, da novi radi a stari vise
   ne radi. Ako se kontejner ne recreira, ne koristiti legacy `up`:
   rucno primeniti kontrolisanu promenu sa istim digestima i overlay-em.
3. Proveriti HTTPS pocetnu, `/api/v1/health`, katalog i bezbednu
   prijavu. Promena `SITE_DOMAIN` zahteva i proveru DNS/Caddy/TLS-a.

Rollback operator potvrdom `CONFIRM_DB_COMPATIBLE=yes` ne vraca bazu;
ovde se koristi samo da sacuva migracioni gate prilikom kontrolisanog
ponovnog aktiviranja iste verzije. Posle incidenta rotirati i kompromitovane
GHCR/SSH tokene zasebno, ako je potrebno.

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
Nakon prvog pinovanog release-a nikada ne koristiti stari
git-pull/Compose --build postupak iz legacy uputstva niti stari image
kao brzi fallback bez provere: stara Alembic revizija moze crash-loopovati.
Ako je sema promenjena nekompatibilno, povratak na legacy zahteva
eksplicitno odobren restore pre-release backup-a u cistu bazu.

**Prvi prelazak** sa rucno gradjene Docker slike nema sacuvan GHCR digest
te stare slike. Pre prvog odobrenog release-a sacuvati checkout, postojece
slike i testiran backup/restore plan (ili rucno uspostaviti pinovani
baseline). Bez toga nema garantovanog brzog rollback-a na staru verziju.

## Ogranicenja

- GitHub Environment prava, SSH pristup, prava za GHCR i firewall nisu
  automatski dokaziva ovim PR-om.
- Testiranje migracija na PostgreSQL iz tiketa #9 ostaje uslov za CD.
- CI na main otkazuje stariji run kada stigne novi commit: SHA bez
  zavrsenog zelenog push run-a namerno nije dozvoljen za release.
- Za Docker Compose release overlay potrebno je izdanje koje podrzava
  YAML !reset (Compose v2.24.4 ili novije); proveriti na staging hostu.
- Proba migracije i baze na stagingu je neophodna i ne zamenjuje je CI.
- Odluka reviewera pre aktivacije mora da potvrdi #9, main-only
  Environment, namenski firewall, staging, postojanje proslog proverljivog
  off-site backup-a i plan nadzora udaljene release sesije. Nisu svi uslovi
  automatski provereni workflow-om.
- Lokalni current/previous GHCR digest-i moraju ostati dostupni za rollback:
  ne pokretati neselektivni `docker image prune -a`. Ako digest zaista
  nedostaje, rollback pokusava samo pull odobrenog SHA256 digest-a;
  dostupnost registrija i dalje moze da bude ogranicenje.
- Rollback aplikacije ne znaci rollback baze.
- Deploy nikada nije automatski posledica merge-a u main.
