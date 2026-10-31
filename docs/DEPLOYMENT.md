# Hostovanje na Hetzneru sa sopstvenim domenom

Ceo postupak traje oko sat vremena. Na kraju sajt radi na `https://tvojdomen.rs`,
ima automatski TLS sertifikat i rate limiting, a izmene kataloga traže admin ključ.

```
internet ──443──▶ Caddy ──/api/*──▶ api (FastAPI) ──▶ db (Postgres)
                    └────────/*───▶ frontend (nginx)
```

Port spolja objavljuje samo Caddy. Baza i aplikacija nisu dostupne sa interneta.

---

## 1. Kupi domen

Bilo koji registrar radi. Za `.rs` domen treba ti registrar ovlašćen kod RNIDS-a
(spisak je na rnids.rs). Za `.com`/`.org`/`.eu` su dobri Cloudflare Registrar
(prodaje po nabavnoj ceni), Porkbun ili Namecheap.

DNS još ne podešavaš, za to ti treba IP servera iz koraka 2.

## 2. Napravi server na Hetzneru

U [Hetzner Cloud Console](https://console.hetzner.cloud):

1. **New project → Add server**
2. **Location:** Falkenstein ili Nuremberg (najbliže Srbiji)
3. **Image:** Ubuntu 24.04
4. **Type:** CX22 (2 vCPU, 4 GB RAM) je dovoljan. CAX11 (ARM) je jeftiniji i
   takođe radi, jer su sve slike multi-arch.
5. **SSH key:** dodaj svoj javni ključ. Ako ga nemaš, napravi ga na laptopu:
   ```bash
   ssh-keygen -t ed25519
   ```
   pa nalepi sadržaj fajla `~/.ssh/id_ed25519.pub`. **Ne biraj prijavu lozinkom.**
6. **Firewalls → Create firewall** i dozvoli samo ove ulazne portove:
   | Protokol | Port | Izvor |
   |---|---|---|
   | TCP | 22 | tvoja IP adresa (ili svuda, ako nemaš fiksnu) |
   | TCP | 80 | svuda |
   | TCP | 443 | svuda |
   | UDP | 443 | svuda |

   Hetzner firewall radi ispred servera, pa ga Docker ne može zaobići. Ovo je
   važno: Docker sam otvara portove i preskače `ufw` na serveru.
7. **Backups:** uključi ih (+20% cene). To su dnevni snimci celog diska.

Zapiši IPv4 adresu servera.

## 3. Usmeri domen na server

Kod registrara, u DNS podešavanjima:

| Tip | Ime | Vrednost |
|---|---|---|
| A | `@` | IPv4 servera |
| AAAA | `@` | IPv6 servera (opciono) |

Ako želiš i `www`, dodaj `CNAME www → tvojdomen.rs` i pogledaj napomenu o `www`
na kraju dokumenta.

Proveri sa laptopa (može da potraje nekoliko minuta):
```bash
nslookup tvojdomen.rs
```
Adresa u odgovoru mora biti IP servera **pre** koraka 6, inače Caddy ne može da
dobije sertifikat.

## 4. Pripremi server

```bash
ssh root@IP_SERVERA
```

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl git unattended-upgrades fail2ban
dpkg-reconfigure -plow unattended-upgrades   # automatske bezbednosne zakrpe
curl -fsSL https://get.docker.com | sh
```

Napravi korisnika za aplikaciju i isključi root prijavu:
```bash
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
mkdir -p /home/deploy/.ssh && cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh

sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

**Pre nego što zatvoriš ovu sesiju**, u novom terminalu proveri da prijava radi:
```bash
ssh deploy@IP_SERVERA
```

## 5. Postavi aplikaciju

Kao `deploy`:
```bash
git clone https://github.com/TVOJ_NALOG/SciConnect.git
cd SciConnect
cp .env.production.example .env.production
chmod 600 .env.production
```

Generiši tajne:
```bash
echo "POSTGRES_PASSWORD=$(openssl rand -base64 36 | tr -d '/+=')"
echo "APP_ADMIN_TOKEN=$(openssl rand -base64 48 | tr -d '\n')"
```

Otvori `.env.production` (`nano .env.production`) i popuni `SITE_DOMAIN`,
`ACME_EMAIL`, `POSTGRES_PASSWORD` i `APP_ADMIN_TOKEN`.

**Admin token sačuvaj u menadžeru lozinki.** Bez njega ne možeš da menjaš katalog.

## 6. Pokreni

```bash
docker compose -f compose.prod.yaml --env-file .env.production up -d --build
docker compose -f compose.prod.yaml --env-file .env.production logs -f caddy api
```

U logu treba da vidiš:
- `certificate obtained successfully` od Caddy-ja
- `Writes require the X-Admin-Token header` od API-ja

Ako API odbije da se pokrene sa `Refusing to start in 'production'`, poruka
navodi tačno koje podešavanje nedostaje ili nije bezbedno.

## 7. Proveri

```bash
D=https://tvojdomen.rs
curl -s -o /dev/null -w "%{http_code}\n" $D/                                   # 200
curl -s -o /dev/null -w "%{http_code}\n" $D/api/v1/catalog/institutions        # 200
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE $D/api/v1/catalog/institutions/1   # 401
curl -s -o /dev/null -w "%{http_code}\n" $D/docs                               # 404
```

U browseru otvori sajt. Na početnoj strani klikni **Try it**, pa
**Sign in as admin** i unesi admin ključ. Ključ ostaje zapamćen dok ne zatvoriš
tab. **Browse as guest** otvara istu aplikaciju samo za čitanje.

Spoljne provere zaglavlja i TLS-a:
- https://securityheaders.com (očekuj ocenu A)
- https://www.ssllabs.com/ssltest (očekuj ocenu A ili A+)

---

## Održavanje

**Nova verzija:**
```bash
cd ~/SciConnect && git pull
docker compose -f compose.prod.yaml --env-file .env.production up -d --build
```
Migracije baze se pokreću same pri startu API-ja.

**Promena admin ključa** (npr. ako je procurio): upiši novi u `.env.production`, pa:
```bash
docker compose -f compose.prod.yaml --env-file .env.production up -d api
```
Stari ključ prestaje da važi odmah, svuda. Admin koji je bio prijavljen biva odjavljen pri sledećoj izmeni, uz poruku da se prijavi ponovo.

**Rezervna kopija baze** (pored Hetzner snimaka). Dodaj u `crontab -e`:
```
0 3 * * * cd /home/deploy/SciConnect && docker compose -f compose.prod.yaml --env-file .env.production exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > /home/deploy/backup-$(date +\%a).sql.gz
```
Tako se čuva poslednjih 7 dana. Povremeno prebaci neku kopiju van servera.

**Vraćanje iz kopije:**
```bash
gunzip -c backup-Mon.sql.gz | docker compose -f compose.prod.yaml --env-file .env.production exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

---

## Šta je zaštićeno, i kako

| Pretnja | Zaštita |
|---|---|
| Neko briše ili menja katalog | Svaki POST/DELETE traži `X-Admin-Token`, a poređenje radi u konstantnom vremenu. API ne može da se pokrene u produkciji bez tokena od bar 32 znaka. |
| Pogađanje admin ključa | Ključ se proverava na `/api/v1/auth/check`, sa posebnim limitom od 5 pokušaja u minuti po IP adresi. Pogrešni pokušaji se beleže u log. |
| Gost menja podatke | Gost ne vidi formulare ni dugmad za brisanje, ali to je samo prikaz. Server odbija svaki upis bez ključa (401), bez obzira šta je u browseru. |
| Skripta zatrpava API | Ograničenje po IP adresi, posebno za čitanje (120/min), upis (20/min) i geokodiranje (10/min), sa `Retry-After` u odgovoru. |
| Lažiranje IP adrese radi zaobilaženja limita | `X-Forwarded-For` se čita tačno jedan skok duboko (Caddy). Zaglavlje koje pošalje klijent se ignoriše. |
| Ogromno telo zahteva | 256 KB u API-ju, 1 MB tvrda granica u Caddy-ju (važi i za chunked telo). |
| Prisluškivanje | Samo HTTPS. HTTP se preusmerava (308), a HSTS važi godinu dana. |
| XSS, clickjacking | Stroga CSP na stranici, `default-src 'none'` na API-ju, `X-Frame-Options: DENY`. |
| Napad na bazu spolja | Port 5432 se ne objavljuje, a Hetzner firewall propušta samo 22/80/443. |
| Mapa endpointa za napadača | `/docs` i `/openapi.json` su isključeni u produkciji, i blokirani na Caddy-ju. |
| Pogrešna konfiguracija | API odbija start sa `*` u CORS-u ili hostovima, sa HTTP origin-om, sa SQLite-om ili bez tokena. |
| Napadi na SSH lozinkom | Prijava samo ključem, root prijava je isključena, a fail2ban blokira pokušaje. |

### Poznata ograničenja

- **Brojači limita žive u memoriji procesa.** Zato API radi sa jednim workerom.
  Restart briše brojače. Za više instanci bi trebao Redis.
- **Jedan admin ključ za sve.** Nema korisničkih naloga ni zapisa o tome ko je šta
  promenio. Ako više ljudi uređuje katalog, sledeći korak je pravi login sistem.
- **`www.tvojdomen.rs`** ne radi dok ga ne dodaš. U `Caddyfile` dodaj blok:
  ```
  www.{$SITE_DOMAIN} {
      redir https://{$SITE_DOMAIN}{uri} permanent
  }
  ```
