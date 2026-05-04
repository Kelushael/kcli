import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api/hostinger`;

// ─── Tiny helpers ────────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const colors = {
    running: 'bg-green-500/20 text-green-400 border-green-500/40',
    stopped: 'bg-red-500/20 text-red-400 border-red-500/40',
    starting: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
    stopping: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
    active: 'bg-green-500/20 text-green-400 border-green-500/40',
    expired: 'bg-red-500/20 text-red-400 border-red-500/40',
    pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  };
  const cls = colors[String(status).toLowerCase()] || 'bg-gray-500/20 text-gray-400 border-gray-500/40';
  return (
    <span className={`px-2 py-0.5 rounded border text-xs font-mono uppercase ${cls}`}>
      {status}
    </span>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12 text-cyan-400 font-mono text-sm animate-pulse">
      Loading...
    </div>
  );
}

function ErrorBox({ message, onRetry }) {
  return (
    <div className="bg-red-900/30 border border-red-500/40 rounded-lg p-4 font-mono text-sm">
      <div className="text-red-400 mb-2">Error</div>
      <div className="text-red-300 text-xs">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 bg-red-700 hover:bg-red-600 text-white px-3 py-1 rounded text-xs transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

function SectionHeader({ title, count, onRefresh, loading }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <span className="text-cyan-400 font-mono font-semibold">{title}</span>
        {count !== undefined && (
          <span className="bg-gray-700 text-gray-400 text-xs px-2 py-0.5 rounded font-mono">{count}</span>
        )}
      </div>
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={loading}
          className="text-gray-500 hover:text-cyan-400 transition-colors text-xs font-mono disabled:opacity-50"
        >
          {loading ? '...' : '↻ Refresh'}
        </button>
      )}
    </div>
  );
}

// ─── VPS Panel ────────────────────────────────────────────────────────────────

function VpsPanel() {
  const [vms, setVms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedVm, setSelectedVm] = useState(null);
  const [actionLoading, setActionLoading] = useState({});

  const loadVms = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/vps/virtual-machines`);
      setVms(res.data?.data || res.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadVms(); }, [loadVms]);

  const vmAction = async (vmId, action) => {
    setActionLoading(prev => ({ ...prev, [`${vmId}-${action}`]: true }));
    try {
      await axios.post(`${API}/vps/virtual-machines/${vmId}/${action}`);
      await loadVms();
    } catch (e) {
      alert(`Failed to ${action} VM: ${e.response?.data?.detail || e.message}`);
    }
    setActionLoading(prev => ({ ...prev, [`${vmId}-${action}`]: false }));
  };

  const isActing = (vmId, action) => actionLoading[`${vmId}-${action}`];

  if (loading && vms.length === 0) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} onRetry={loadVms} />;

  return (
    <div>
      <SectionHeader title="Virtual Machines" count={vms.length} onRefresh={loadVms} loading={loading} />
      {vms.length === 0 ? (
        <div className="text-gray-500 font-mono text-sm text-center py-8">No virtual machines found</div>
      ) : (
        <div className="space-y-3">
          {vms.map((vm) => (
            <div
              key={vm.id}
              className="bg-gray-800/60 border border-gray-700/60 rounded-lg overflow-hidden"
            >
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-800 transition-colors"
                onClick={() => setSelectedVm(selectedVm?.id === vm.id ? null : vm)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-lg">🖥</span>
                  <div className="min-w-0">
                    <div className="text-gray-100 font-mono text-sm font-semibold truncate">
                      {vm.hostname || vm.label || `VM #${vm.id}`}
                    </div>
                    <div className="text-gray-500 text-xs font-mono">
                      {vm.main_ip_address || vm.ip || '—'}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge status={vm.state || vm.status || 'unknown'} />
                  <span className="text-gray-600 text-xs">{selectedVm?.id === vm.id ? '▲' : '▼'}</span>
                </div>
              </div>

              {/* Expanded details */}
              {selectedVm?.id === vm.id && (
                <div className="border-t border-gray-700/40 p-3 bg-gray-900/40">
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono mb-4">
                    {vm.plan && (
                      <div><span className="text-gray-500">Plan:</span> <span className="text-gray-300">{vm.plan}</span></div>
                    )}
                    {vm.cpus !== undefined && (
                      <div><span className="text-gray-500">CPUs:</span> <span className="text-gray-300">{vm.cpus}</span></div>
                    )}
                    {vm.memory !== undefined && (
                      <div><span className="text-gray-500">RAM:</span> <span className="text-gray-300">{vm.memory} MB</span></div>
                    )}
                    {vm.disk !== undefined && (
                      <div><span className="text-gray-500">Disk:</span> <span className="text-gray-300">{vm.disk} GB</span></div>
                    )}
                    {vm.template && (
                      <div className="col-span-2"><span className="text-gray-500">OS:</span> <span className="text-gray-300">{vm.template?.name || vm.template}</span></div>
                    )}
                    {vm.data_center && (
                      <div className="col-span-2"><span className="text-gray-500">Datacenter:</span> <span className="text-gray-300">{vm.data_center?.name || vm.data_center?.location || vm.data_center}</span></div>
                    )}
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => vmAction(vm.id, 'start')}
                      disabled={isActing(vm.id, 'start')}
                      className="bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-xs font-mono py-1 px-3 rounded transition-colors"
                      data-testid={`vm-start-${vm.id}`}
                    >
                      {isActing(vm.id, 'start') ? '...' : '▶ Start'}
                    </button>
                    <button
                      onClick={() => vmAction(vm.id, 'stop')}
                      disabled={isActing(vm.id, 'stop')}
                      className="bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white text-xs font-mono py-1 px-3 rounded transition-colors"
                      data-testid={`vm-stop-${vm.id}`}
                    >
                      {isActing(vm.id, 'stop') ? '...' : '⏹ Stop'}
                    </button>
                    <button
                      onClick={() => vmAction(vm.id, 'restart')}
                      disabled={isActing(vm.id, 'restart')}
                      className="bg-yellow-700 hover:bg-yellow-600 disabled:opacity-50 text-white text-xs font-mono py-1 px-3 rounded transition-colors"
                      data-testid={`vm-restart-${vm.id}`}
                    >
                      {isActing(vm.id, 'restart') ? '...' : '↺ Restart'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Domains Panel ────────────────────────────────────────────────────────────

function DomainsPanel() {
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedDomain, setSelectedDomain] = useState(null);
  const [dnsZone, setDnsZone] = useState(null);
  const [dnsLoading, setDnsLoading] = useState(false);

  const loadDomains = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/domains/portfolio`);
      setDomains(res.data?.data || res.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadDomains(); }, [loadDomains]);

  const loadDnsZone = async (domain) => {
    if (selectedDomain === domain) {
      setSelectedDomain(null);
      setDnsZone(null);
      return;
    }
    setSelectedDomain(domain);
    setDnsLoading(true);
    setDnsZone(null);
    try {
      const res = await axios.get(`${API}/dns/zones/${domain}`);
      setDnsZone(res.data?.data || res.data || []);
    } catch (e) {
      setDnsZone({ error: e.response?.data?.detail || e.message });
    }
    setDnsLoading(false);
  };

  if (loading && domains.length === 0) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} onRetry={loadDomains} />;

  return (
    <div>
      <SectionHeader title="Domains" count={domains.length} onRefresh={loadDomains} loading={loading} />
      {domains.length === 0 ? (
        <div className="text-gray-500 font-mono text-sm text-center py-8">No domains found</div>
      ) : (
        <div className="space-y-2">
          {domains.map((d) => {
            const domainName = d.domain || d.name || d;
            const expiresAt = d.expires_at || d.expiry_date;
            const isExpiringSoon = expiresAt && new Date(expiresAt) < new Date(Date.now() + 30 * 24 * 3600 * 1000);

            return (
              <div key={domainName} className="bg-gray-800/60 border border-gray-700/60 rounded-lg overflow-hidden">
                <div
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-800 transition-colors"
                  onClick={() => loadDnsZone(domainName)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-base">🌐</span>
                    <div className="min-w-0">
                      <div className="text-gray-100 font-mono text-sm font-semibold truncate">{domainName}</div>
                      {expiresAt && (
                        <div className={`text-xs font-mono ${isExpiringSoon ? 'text-yellow-400' : 'text-gray-500'}`}>
                          Expires: {new Date(expiresAt).toLocaleDateString()}
                          {isExpiringSoon && ' ⚠'}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {d.status && <StatusBadge status={d.status} />}
                    <span className="text-gray-600 text-xs">{selectedDomain === domainName ? '▲' : '▼'}</span>
                  </div>
                </div>

                {/* DNS Records */}
                {selectedDomain === domainName && (
                  <div className="border-t border-gray-700/40 p-3 bg-gray-900/40">
                    <div className="text-cyan-400 font-mono text-xs mb-3">DNS Zone Records</div>
                    {dnsLoading ? (
                      <div className="text-gray-500 font-mono text-xs animate-pulse">Loading DNS records...</div>
                    ) : dnsZone?.error ? (
                      <div className="text-red-400 font-mono text-xs">{dnsZone.error}</div>
                    ) : Array.isArray(dnsZone) && dnsZone.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs font-mono">
                          <thead>
                            <tr className="text-gray-500 border-b border-gray-700/40">
                              <th className="text-left pb-1 pr-3">Type</th>
                              <th className="text-left pb-1 pr-3">Name</th>
                              <th className="text-left pb-1 pr-3">Value</th>
                              <th className="text-left pb-1">TTL</th>
                            </tr>
                          </thead>
                          <tbody>
                            {dnsZone.map((record, idx) => (
                              <tr key={idx} className="border-b border-gray-800/40 hover:bg-gray-800/30">
                                <td className="py-1 pr-3 text-yellow-400">{record.type}</td>
                                <td className="py-1 pr-3 text-gray-300 max-w-[120px] truncate" title={record.name}>{record.name}</td>
                                <td className="py-1 pr-3 text-gray-400 max-w-[200px] truncate" title={record.content || record.value}>{record.content || record.value}</td>
                                <td className="py-1 text-gray-500">{record.ttl}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="text-gray-500 text-xs font-mono">No DNS records found</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── DNS Panel (search by domain) ────────────────────────────────────────────

function DnsPanel() {
  const [domain, setDomain] = useState('');
  const [zone, setZone] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchZone = async () => {
    if (!domain.trim()) return;
    setLoading(true);
    setError(null);
    setZone(null);
    try {
      const res = await axios.get(`${API}/dns/zones/${domain.trim()}`);
      setZone(res.data?.data || res.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  return (
    <div>
      <SectionHeader title="DNS Zone Lookup" />
      <div className="flex gap-2 mb-4">
        <input
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchZone()}
          placeholder="example.com"
          className="flex-1 bg-gray-800 border border-gray-700 focus:border-cyan-500 rounded px-3 py-2 text-gray-100 font-mono text-sm focus:outline-none"
        />
        <button
          onClick={fetchZone}
          disabled={loading || !domain.trim()}
          className="bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-white font-mono text-sm px-4 py-2 rounded transition-colors"
        >
          {loading ? '...' : 'Lookup'}
        </button>
      </div>

      {error && <ErrorBox message={error} />}

      {Array.isArray(zone) && (
        <div>
          <div className="text-gray-500 font-mono text-xs mb-2">{zone.length} records for <span className="text-cyan-400">{domain}</span></div>
          {zone.length === 0 ? (
            <div className="text-gray-600 font-mono text-sm text-center py-4">No records found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono border-collapse">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700">
                    <th className="text-left py-2 pr-3">Type</th>
                    <th className="text-left py-2 pr-3">Name</th>
                    <th className="text-left py-2 pr-3">Value</th>
                    <th className="text-left py-2">TTL</th>
                  </tr>
                </thead>
                <tbody>
                  {zone.map((r, i) => (
                    <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/40">
                      <td className="py-1.5 pr-3 text-yellow-400 font-semibold">{r.type}</td>
                      <td className="py-1.5 pr-3 text-gray-300">{r.name}</td>
                      <td className="py-1.5 pr-3 text-gray-400 max-w-xs truncate" title={r.content || r.value}>{r.content || r.value}</td>
                      <td className="py-1.5 text-gray-500">{r.ttl}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Billing Panel ────────────────────────────────────────────────────────────

function BillingPanel() {
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadSubscriptions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/billing/subscriptions`);
      setSubscriptions(res.data?.data || res.data || []);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadSubscriptions(); }, [loadSubscriptions]);

  if (loading && subscriptions.length === 0) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} onRetry={loadSubscriptions} />;

  return (
    <div>
      <SectionHeader title="Subscriptions" count={subscriptions.length} onRefresh={loadSubscriptions} loading={loading} />
      {subscriptions.length === 0 ? (
        <div className="text-gray-500 font-mono text-sm text-center py-8">No subscriptions found</div>
      ) : (
        <div className="space-y-2">
          {subscriptions.map((sub, idx) => {
            const expiresAt = sub.expires_at || sub.expiry_date;
            const isExpiringSoon = expiresAt && new Date(expiresAt) < new Date(Date.now() + 30 * 24 * 3600 * 1000);
            return (
              <div key={sub.id || idx} className="bg-gray-800/60 border border-gray-700/60 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-gray-100 font-mono text-sm font-semibold">
                      {sub.name || sub.plan || `Subscription #${sub.id}`}
                    </div>
                    <div className="text-gray-500 font-mono text-xs mt-0.5">
                      {sub.activated_at && `Activated: ${new Date(sub.activated_at).toLocaleDateString()}`}
                      {expiresAt && (
                        <span className={`ml-2 ${isExpiringSoon ? 'text-yellow-400' : ''}`}>
                          Expires: {new Date(expiresAt).toLocaleDateString()}
                          {isExpiringSoon && ' ⚠'}
                        </span>
                      )}
                    </div>
                  </div>
                  {sub.status && <StatusBadge status={sub.status} />}
                </div>
                {sub.auto_renewal !== undefined && (
                  <div className="text-gray-500 font-mono text-xs mt-1">
                    Auto-renewal: <span className={sub.auto_renewal ? 'text-green-400' : 'text-gray-400'}>{sub.auto_renewal ? 'On' : 'Off'}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Main HostingerPanel component ───────────────────────────────────────────

const TABS = [
  { id: 'vps', label: '🖥 VPS', component: VpsPanel },
  { id: 'domains', label: '🌐 Domains', component: DomainsPanel },
  { id: 'dns', label: '📋 DNS', component: DnsPanel },
  { id: 'billing', label: '💳 Billing', component: BillingPanel },
];

export default function HostingerPanel({ onClose }) {
  const [activeTab, setActiveTab] = useState('vps');
  const [configured, setConfigured] = useState(null);

  useEffect(() => {
    axios.get(`${API}/config`)
      .then((res) => setConfigured(res.data.configured))
      .catch(() => setConfigured(false));
  }, []);

  const ActiveComponent = TABS.find((t) => t.id === activeTab)?.component;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4" data-testid="hostinger-panel">
      <div className="bg-gray-950 border border-orange-500/60 rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-orange-500/30 bg-gray-900/60">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🏠</span>
            <div>
              <h2 className="text-orange-400 font-mono font-bold text-lg">Hostinger</h2>
              <div className="text-gray-500 font-mono text-xs">
                {configured === null
                  ? 'Checking...'
                  : configured
                  ? '● API Connected'
                  : '○ API Token not configured'}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors text-xl leading-none"
            data-testid="hostinger-close-btn"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800 bg-gray-900/40 shrink-0">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 font-mono text-sm transition-colors ${
                activeTab === tab.id
                  ? 'text-orange-400 border-b-2 border-orange-400 bg-gray-950/40'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
              data-testid={`hostinger-tab-${tab.id}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {configured === false ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="text-4xl mb-4">🔑</div>
              <h3 className="text-gray-300 font-mono font-semibold mb-2">API Token Required</h3>
              <p className="text-gray-500 font-mono text-sm max-w-sm">
                Set the <span className="text-orange-400">HOSTINGER_API_TOKEN</span> environment variable to connect to the Hostinger API.
              </p>
              <div className="mt-4 bg-gray-900 border border-gray-700 rounded p-3 font-mono text-xs text-green-400">
                HOSTINGER_API_TOKEN=your_token_here
              </div>
            </div>
          ) : configured === null ? (
            <LoadingSpinner />
          ) : (
            <ActiveComponent />
          )}
        </div>
      </div>
    </div>
  );
}
