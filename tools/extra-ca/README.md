# Extra root certificates

Leave this folder empty unless the Docker build fails with:

```
unable to get local issuer certificate
```

That means something on your machine intercepts HTTPS and re-signs
certificates. It is usually an antivirus "web shield" (Norton, Avast, Kaspersky
and others) or a university or corporate proxy. Windows trusts that product's
root certificate. A fresh Linux container does not, so every download fails.

The fix is to give the container the same root certificate Windows already has.

## 1. Find out who is intercepting

In the container, or anywhere with `openssl`:

```bash
echo | openssl s_client -connect github.com:443 -servername github.com 2>/dev/null | openssl x509 -noout -issuer
```

A normal result names a public authority such as Sectigo or DigiCert. If it
names your antivirus or your organisation instead, that is the interceptor.

## 2. Export its root certificate (Windows, PowerShell)

Change `Norton` to whatever name step 1 printed:

```bash
$c = Get-ChildItem Cert:\LocalMachine\Root | Where-Object Subject -match 'Norton' | Select-Object -First 1; $pem = "-----BEGIN CERTIFICATE-----`n" + ([Convert]::ToBase64String($c.RawData) -replace '(.{64})', "`$1`n").TrimEnd("`n") + "`n-----END CERTIFICATE-----`n"; [IO.File]::WriteAllText("$PWD\tools\extra-ca\interceptor.crt", $pem)
```

Run it from the repo root. It writes `tools/extra-ca/interceptor.crt`.

## 3. Rebuild

```bash
tools/docker_run.sh build
```

## Do not commit these

`.gitignore` excludes `*.crt` and `*.pem` in this folder. The certificate
belongs to your machine's antivirus, not to the project. Another student's
machine will have a different one, or none.

## Is this safe?

The container ends up trusting exactly what your Windows install already
trusts: nothing more. If you would rather not do it, you can instead configure
the antivirus to stop scanning HTTPS for Docker. That is a setting only you
should change, in the antivirus itself.
