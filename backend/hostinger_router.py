from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import os
import logging

logger = logging.getLogger(__name__)

HOSTINGER_API_TOKEN = os.getenv("HOSTINGER_API_TOKEN", "")
HOSTINGER_BASE_URL = "https://developers.hostinger.com"

router = APIRouter(prefix="/api/hostinger", tags=["hostinger"])


class HostingerClient:
    def __init__(self, token: str):
        self.base_url = HOSTINGER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                **kwargs,
            )
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Hostinger API token invalid or expired")
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Resource not found: {path}")
            if response.status_code == 429:
                raise HTTPException(status_code=429, detail="Hostinger API rate limit exceeded")
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text[:500])
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

    async def get(self, path: str, params: Dict = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, data: Dict = None) -> Any:
        return await self._request("POST", path, json=data)

    async def put(self, path: str, data: Dict = None) -> Any:
        return await self._request("PUT", path, json=data)

    async def delete(self, path: str) -> Any:
        return await self._request("DELETE", path)


def get_client() -> HostingerClient:
    if not HOSTINGER_API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Hostinger API token not configured. Set HOSTINGER_API_TOKEN environment variable.",
        )
    return HostingerClient(HOSTINGER_API_TOKEN)


# ===== CONFIG =====

@router.get("/config")
async def get_hostinger_config():
    return {"configured": bool(HOSTINGER_API_TOKEN)}


# ===== VPS: Virtual Machines =====

@router.get("/vps/virtual-machines")
async def list_virtual_machines():
    return await get_client().get("/api/vps/v1/virtual-machines")


@router.get("/vps/virtual-machines/{vm_id}")
async def get_virtual_machine(vm_id: int):
    return await get_client().get(f"/api/vps/v1/virtual-machines/{vm_id}")


@router.get("/vps/virtual-machines/{vm_id}/metrics")
async def get_vm_metrics(
    vm_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    return await get_client().get(f"/api/vps/v1/virtual-machines/{vm_id}/metrics", params=params or None)


@router.post("/vps/virtual-machines/{vm_id}/start")
async def start_vm(vm_id: int):
    return await get_client().post(f"/api/vps/v1/virtual-machines/{vm_id}/start")


@router.post("/vps/virtual-machines/{vm_id}/stop")
async def stop_vm(vm_id: int):
    return await get_client().post(f"/api/vps/v1/virtual-machines/{vm_id}/stop")


@router.post("/vps/virtual-machines/{vm_id}/restart")
async def restart_vm(vm_id: int):
    return await get_client().post(f"/api/vps/v1/virtual-machines/{vm_id}/restart")


@router.get("/vps/virtual-machines/{vm_id}/backups")
async def list_vm_backups(vm_id: int):
    return await get_client().get(f"/api/vps/v1/virtual-machines/{vm_id}/backups")


@router.get("/vps/virtual-machines/{vm_id}/actions")
async def list_vm_actions(vm_id: int):
    return await get_client().get(f"/api/vps/v1/virtual-machines/{vm_id}/actions")


@router.get("/vps/virtual-machines/{vm_id}/snapshot")
async def get_vm_snapshot(vm_id: int):
    return await get_client().get(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")


@router.post("/vps/virtual-machines/{vm_id}/snapshot")
async def create_vm_snapshot(vm_id: int):
    return await get_client().post(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")


@router.delete("/vps/virtual-machines/{vm_id}/snapshot")
async def delete_vm_snapshot(vm_id: int):
    return await get_client().delete(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")


@router.post("/vps/virtual-machines/{vm_id}/snapshot/restore")
async def restore_vm_snapshot(vm_id: int):
    return await get_client().post(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot/restore")


@router.get("/vps/virtual-machines/{vm_id}/public-keys")
async def list_vm_public_keys(vm_id: int):
    return await get_client().get(f"/api/vps/v1/virtual-machines/{vm_id}/public-keys")


# ===== VPS: Data Centers / Templates / Keys =====

@router.get("/vps/data-centers")
async def list_data_centers():
    return await get_client().get("/api/vps/v1/data-centers")


@router.get("/vps/templates")
async def list_os_templates():
    return await get_client().get("/api/vps/v1/templates")


@router.get("/vps/public-keys")
async def list_public_keys(page: int = 1):
    return await get_client().get("/api/vps/v1/public-keys", params={"page": page})


@router.get("/vps/firewall")
async def list_firewalls():
    return await get_client().get("/api/vps/v1/firewall")


@router.get("/vps/post-install-scripts")
async def list_post_install_scripts():
    return await get_client().get("/api/vps/v1/post-install-scripts")


# ===== DNS =====

@router.get("/dns/zones/{domain}")
async def get_dns_zone(domain: str):
    return await get_client().get(f"/api/dns/v1/zones/{domain}")


class DnsZoneUpdate(BaseModel):
    zone: Optional[List[Dict[str, Any]]] = None


@router.put("/dns/zones/{domain}")
async def update_dns_zone(domain: str, data: DnsZoneUpdate):
    return await get_client().put(f"/api/dns/v1/zones/{domain}", data=data.model_dump(exclude_none=True))


@router.delete("/dns/zones/{domain}")
async def delete_dns_zone(domain: str):
    return await get_client().delete(f"/api/dns/v1/zones/{domain}")


@router.post("/dns/zones/{domain}/reset")
async def reset_dns_zone(domain: str):
    return await get_client().post(f"/api/dns/v1/zones/{domain}/reset")


@router.get("/dns/snapshots/{domain}")
async def list_dns_snapshots(domain: str):
    return await get_client().get(f"/api/dns/v1/snapshots/{domain}")


@router.post("/dns/snapshots/{domain}/{snapshot_id}/restore")
async def restore_dns_snapshot(domain: str, snapshot_id: str):
    return await get_client().post(f"/api/dns/v1/snapshots/{domain}/{snapshot_id}/restore")


# ===== Domains =====

@router.get("/domains/portfolio")
async def list_domains(page: int = 1):
    return await get_client().get("/api/domains/v1/portfolio", params={"page": page})


@router.get("/domains/portfolio/{domain}")
async def get_domain(domain: str):
    return await get_client().get(f"/api/domains/v1/portfolio/{domain}")


class DomainAvailabilityRequest(BaseModel):
    domains: List[str]


@router.post("/domains/availability")
async def check_domain_availability(data: DomainAvailabilityRequest):
    return await get_client().post("/api/domains/v1/availability", data=data.model_dump())


@router.get("/domains/whois")
async def list_whois_profiles():
    return await get_client().get("/api/domains/v1/whois")


@router.get("/domains/whois/{whois_id}")
async def get_whois_profile(whois_id: int):
    return await get_client().get(f"/api/domains/v1/whois/{whois_id}")


@router.get("/domains/forwarding/{domain}")
async def get_domain_forwarding(domain: str):
    return await get_client().get(f"/api/domains/v1/forwarding/{domain}")


# ===== Billing =====

@router.get("/billing/subscriptions")
async def list_subscriptions():
    return await get_client().get("/api/billing/v1/subscriptions")


@router.get("/billing/catalog")
async def get_catalog():
    return await get_client().get("/api/billing/v1/catalog")


@router.get("/billing/payment-methods")
async def list_payment_methods():
    return await get_client().get("/api/billing/v1/payment-methods")


# ===== Hosting =====

@router.get("/hosting/orders")
async def list_hosting_orders():
    return await get_client().get("/api/hosting/v1/orders")


@router.get("/hosting/datacenters")
async def list_hosting_datacenters():
    return await get_client().get("/api/hosting/v1/datacenters")


@router.get("/hosting/websites")
async def list_websites():
    return await get_client().get("/api/hosting/v1/websites")
