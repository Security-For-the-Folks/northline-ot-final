#!/bin/bash
set -e

_t() { python3 -c 'import sys;k=b"MW-ENG-01/DC-EAST";b=bytes.fromhex(sys.argv[1]);print(bytes(c^k[i%len(k)] for i,c in enumerate(b)).decode())' "$1"; }

# Per-start tokens.
sed -i "s|@@BUILD_TOKEN@@|$(_t 0b1b6c02350b6b016e1f14707f7115630612071d171a73614d)|" /opt/portal/config/operators.conf
_t 0b1b6c0235027a636e697473790d711f1012147f710d0c1e744c > /home/svc_maint/flag.txt
chown svc_maint:svc_maint /home/svc_maint/flag.txt
chmod 644 /home/svc_maint/flag.txt

python3 /opt/portal/portal.py >/var/log/portal.log 2>&1 &
echo "MW-ENG-01 up"
exec /usr/sbin/sshd -D -e
