"""
kubectl_secret.py - Create k8s secrets from OS credential store.

Pulls credentials from Windows Credential Manager / macOS Keychain
and pipes them to kubectl without exposing values in shell history or logs.

Usage:
    python kubectl_secret.py \
      --name openclaw-secrets \
      --namespace joelg-moltbot \
      --key rdsec/API_KEY:RDSEC_API_KEY \
      --key telegram/BOT_TOKEN:TELEGRAM_BOT_TOKEN

Each --key is CRED_STORE_KEY:K8S_ENV_NAME
  - CRED_STORE_KEY = key in OS credential store (e.g. rdsec/API_KEY)
  - K8S_ENV_NAME = env var name in the k8s secret (e.g. RDSEC_API_KEY)
"""
import argparse
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claude_cred import resolve

def main():
    parser = argparse.ArgumentParser(description="Create k8s secret from OS credential store")
    parser.add_argument("--name", required=True, help="Secret name")
    parser.add_argument("--namespace", required=True, help="K8s namespace")
    parser.add_argument("--key", action="append", required=True,
                        help="CRED_KEY:K8S_NAME mapping (repeatable)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print command structure without values")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    args = parser.parse_args()

    # Resolve all credentials first
    mappings = []
    for key_spec in args.key:
        if ":" not in key_spec:
            print(f"ERROR: --key must be CRED_KEY:K8S_NAME, got: {key_spec}", file=sys.stderr)
            sys.exit(1)
        cred_key, k8s_name = key_spec.split(":", 1)
        try:
            value = resolve(cred_key)
            mappings.append((k8s_name, value))
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print(f"Store it first: python store_gui.py {cred_key}", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        print(f"kubectl create secret generic {args.name} \\")
        print(f"  --namespace={args.namespace} \\")
        for k8s_name, _ in mappings:
            print(f"  --from-literal={k8s_name}=<from-credential-store> \\")
        print("  --dry-run=client -o yaml | kubectl apply -f -")
        return

    # Build kubectl command
    cmd = [
        "kubectl", "create", "secret", "generic", args.name,
        f"--namespace={args.namespace}",
    ]
    if args.kubeconfig:
        cmd.insert(1, f"--kubeconfig={args.kubeconfig}")

    for k8s_name, value in mappings:
        cmd.append(f"--from-literal={k8s_name}={value}")

    cmd.extend(["--dry-run=client", "-o", "yaml"])

    # Pipe through kubectl apply to handle create-or-update
    create_proc = subprocess.run(cmd, capture_output=True, text=True)
    if create_proc.returncode != 0:
        print(f"ERROR: kubectl create failed: {create_proc.stderr}", file=sys.stderr)
        sys.exit(1)

    apply_cmd = ["kubectl", "apply", "-f", "-"]
    if args.kubeconfig:
        apply_cmd.insert(1, f"--kubeconfig={args.kubeconfig}")
    if args.namespace:
        apply_cmd.extend([f"--namespace={args.namespace}"])

    apply_proc = subprocess.run(apply_cmd, input=create_proc.stdout, capture_output=True, text=True)
    if apply_proc.returncode != 0:
        print(f"ERROR: kubectl apply failed: {apply_proc.stderr}", file=sys.stderr)
        sys.exit(1)

    print(apply_proc.stdout.strip())

    # Zero out credential values from memory
    for i, (_, _) in enumerate(mappings):
        mappings[i] = (mappings[i][0], "x" * len(mappings[i][1]))

if __name__ == "__main__":
    main()
