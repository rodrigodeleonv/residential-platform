# Deployment

Production runs from [`docker-compose.prod.yml`](../docker-compose.prod.yml): PostgreSQL + API containers. The same stack works on any Docker host, cloud VM or on-premises — nothing is installed on the host OS besides Docker and a reverse proxy.

## One-time setup

1. Install Docker (with the compose plugin) on the host and clone the repository.
2. Create a `.env` file at the repository root (read by compose for `${...}` interpolation):

   ```dotenv
   POSTGRES_PASSWORD=<strong random password>
   APP_BASE_URL=https://condo.example.com   # public URL, used in login-link emails
   ```

3. Optionally create `api.env` at the repository root with the deployment's policy values (currency, timezone, visit windows, rate limits, ...). Copy [`apps/api/example.env`](../apps/api/example.env) as a starting point and keep only the `APP_*` lines you want to override — database URL and environment are pinned by the compose file and cannot be overridden here.
4. Start the stack (migrations run automatically when the api container starts):

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

5. Create the first admin account:

   ```bash
   docker compose -f docker-compose.prod.yml exec api python -m app.bootstrap
   ```

## TLS / reverse proxy

The API binds to `127.0.0.1:8000` on the host — it is not reachable from outside. Put a TLS-terminating reverse proxy (Caddy, nginx, ...) on the same host in front of it. HTTPS is mandatory in production: session cookies are set with the `Secure` flag and will not work over plain HTTP.

The proxy must forward `X-Forwarded-For` / `X-Forwarded-Proto`; uvicorn runs with `--proxy-headers` and trusts them from any peer (`FORWARDED_ALLOW_IPS=*`), which is safe only because the port is local-only. If you expose the api port differently (e.g. a cloud load balancer over a private network), restrict `FORWARDED_ALLOW_IPS` to the proxy's address. The client IP matters: login endpoints are rate-limited per IP.

Example Caddyfile (Caddy obtains and renews certificates automatically):

```
condo.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

## Updating

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Pending migrations apply on start. Postgres data lives in the `pgdata` named volume and survives rebuilds.

## Backups

Dump the database from the running container (schedule via cron on the host):

```bash
docker compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U residential residential > backup-$(date +%F).sql
```

Restore with `psql -U residential residential < backup-....sql` inside the container.

## Current limitations

- The email provider is still the console mock (`APP_EMAIL_PROVIDER=console`): login codes are printed to the api container logs (`docker compose -f docker-compose.prod.yml logs -f api`) instead of being emailed. A real provider behind the same interface is pending.
- Single api replica by design (in-process rate limiter, migrations on start). Scale target is a few hundred users; one container is plenty.
