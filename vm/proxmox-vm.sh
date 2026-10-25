#!/bin/bash
# TV Streamer – create the streamer VM on a Proxmox VE host.
# Run in the Proxmox shell (node → Shell) as root:
#   curl -fsSLo /root/tv-streamer-vm.sh https://raw.githubusercontent.com/SebastianEitzert/TV-Streamer/main/vm/proxmox-vm.sh
#   bash /root/tv-streamer-vm.sh
# Every value can be preset as an environment variable, e.g. VMID=120 IP=192.168.1.42/24 GW=192.168.1.1 bash ...
# Undo: qm stop $VMID; qm destroy $VMID --purge; rm /var/lib/vz/snippets/tv-streamer-vendor.yaml
set -euo pipefail

ask() { # ask VAR "question" default
  local cur="${!1:-}"
  if [ -z "$cur" ]; then read -r -p "$2 [$3]: " cur; cur="${cur:-$3}"; fi
  printf -v "$1" '%s' "$cur"
}

[ "$(id -u)" = 0 ] || { echo "Please run as root."; exit 1; }
command -v qm >/dev/null || { echo "This is not a Proxmox VE host."; exit 1; }

ask VMID   "VM ID"                                   "$(pvesh get /cluster/nextid)"
ask NAME   "VM name"                                 "tv-streamer"
ask IP     "IP address with prefix, or dhcp"         "dhcp"
[ "$IP" = dhcp ] || ask GW "Gateway"                 ""
ask BRIDGE "Network bridge"                          "vmbr0"
ask STORE  "Storage for the disk"                    "local-lvm"
ask CORES  "CPU cores (2 TVs: 8 recommended)"        "4"
ask MEM    "RAM in MB (2 TVs: 6144 recommended)"     "4096"
ask DISK   "Disk size"                               "20G"

[ ! -e "/etc/pve/qemu-server/$VMID.conf" ] && [ ! -e "/etc/pve/lxc/$VMID.conf" ] || { echo "ID $VMID is taken – nothing changed."; exit 1; }

while true; do
  read -r -s -p "Password for user tv in the VM (console login): " PW; echo
  read -r -s -p "Repeat password: " PW2; echo
  [ -n "$PW" ] && [ "$PW" = "$PW2" ] && break
  echo "Empty or different – please try again."
done

IMG_NAME=debian-13-genericcloud-amd64.qcow2
IMG_URL=https://cloud.debian.org/images/cloud/trixie/latest/$IMG_NAME
SUMS_URL=https://cloud.debian.org/images/cloud/trixie/latest/SHA512SUMS
IMG=/var/lib/vz/import/$IMG_NAME
SNIP_NAME=tv-streamer-vendor.yaml
SNIP=/var/lib/vz/snippets/$SNIP_NAME

echo "== Debian 13 cloud image"
mkdir -p /var/lib/vz/import
if [ ! -s "$IMG" ]; then
  curl -fL --progress-bar -o "$IMG.new" "$IMG_URL"
  WANT=$(curl -fsSL "$SUMS_URL" | awk -v n="$IMG_NAME" '$2==n {print $1}' || true)
  HAVE=$(sha512sum "$IMG.new" | awk '{print $1}')
  if [ -n "$WANT" ] && [ "$WANT" != "$HAVE" ]; then rm -f "$IMG.new"; echo "Checksum mismatch – aborted."; exit 1; fi
  mv "$IMG.new" "$IMG"
fi

echo "== Storage local: content type snippets"
CONTENT=$(awk '$1=="dir:" && $2=="local" {f=1; next} /^[a-z]/ {f=0} f && $1=="content" {print $2}' /etc/pve/storage.cfg)
case ",$CONTENT," in *,snippets,*) ;; *) pvesm set local --content "$CONTENT,snippets" ;; esac
mkdir -p /var/lib/vz/snippets
cat > "$SNIP" <<'EOF'
#cloud-config
# TV Streamer – first boot: guest agent and Docker
package_update: true
packages: [qemu-guest-agent, curl, ca-certificates]
runcmd:
  - [systemctl, start, qemu-guest-agent]
  - [sh, -c, "curl -fsSL https://get.docker.com | sh > /var/log/tv-streamer-docker.log 2>&1"]
  - [mkdir, -p, /opt/tv-streamer]
EOF

echo "== Create VM $VMID"
if [ "$IP" = dhcp ]; then IPCFG="ip=dhcp"; else IPCFG="ip=$IP,gw=$GW"; fi
qm create "$VMID" --name "$NAME" --ostype l26 --machine q35 --cpu host --cores "$CORES" --cpuunits 50 \
  --memory "$MEM" --balloon "$((MEM / 2))" --scsihw virtio-scsi-single \
  --scsi0 "$STORE:0,import-from=$IMG,discard=on,ssd=1,iothread=1" --ide2 "$STORE:cloudinit" --boot order=scsi0 \
  --net0 "virtio,bridge=$BRIDGE" --serial0 socket --vga serial0 --agent enabled=1,fstrim_cloned_disks=1 --onboot 1 \
  --ciuser tv --cipassword "$PW" --ipconfig0 "$IPCFG" --cicustom "vendor=local:snippets/$SNIP_NAME"
unset PW PW2
qm disk resize "$VMID" scsi0 "$DISK"
qm start "$VMID"

cat <<EOF

Done – VM $VMID "$NAME" is starting and installs Docker by itself (about 5 minutes).
Console: VM $VMID → Console, user tv. Check: sudo docker version
Next: add the integration in Home Assistant and run the "VM setup" command on this VM (see README).
EOF
