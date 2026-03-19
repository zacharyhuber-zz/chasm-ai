import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Zap, Users, Search } from 'lucide-react';
import Sidebar from './components/Sidebar';
import OpportunityFeed from './components/OpportunityFeed';
import PersonaExplorer from './components/PersonaExplorer';
import GalaxyMap from './components/GalaxyMap';
import StatsBar from './components/StatsBar';
import EvidenceDrawer from './components/EvidenceDrawer';
import Interview from './components/Interview';
import {
  fetchProducts,
  fetchGraph,
  fetchOpportunities,
  onboardCompany,
  type ProductNode,
  type GraphData,
} from './api';

type ViewMode = 'opportunities' | 'personas' | 'research';

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  return hash;
}

export default function App() {
  const hash = useHashRoute();

  // Check if we're on an interview route: #/interview/{sessionId}
  const interviewMatch = hash.match(/^#\/interview\/(.+)$/);
  if (interviewMatch) {
    return <Interview sessionId={interviewMatch[1]} />;
  }

  return <Dashboard />;
}

function Dashboard() {
  const [products, setProducts] = useState<ProductNode[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<ProductNode | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('opportunities');

  // Opportunity-centric stats
  const [opportunityCount, setOpportunityCount] = useState(0);
  const [highSeverityCount, setHighSeverityCount] = useState(0);

  // Evidence Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerNodeIds, setDrawerNodeIds] = useState<string[]>([]);
  const [drawerTitle, setDrawerTitle] = useState('');

  // Onboarding modal state
  const [showOnboardModal, setShowOnboardModal] = useState(false);
  const [onboardUrl, setOnboardUrl] = useState('');
  const [onboarding, setOnboarding] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [prods, graph] = await Promise.all([fetchProducts(), fetchGraph()]);
      setProducts(prods);
      setGraphData(graph);
    } catch {
      setError('Could not connect to Chasm API. Is the backend running on port 8000?');
      setProducts([]);
      setGraphData({ nodes: [], links: [] });
    } finally {
      setLoading(false);
    }
  }, []);

  // Load opportunity stats when product changes
  useEffect(() => {
    if (!selectedProduct) {
      setOpportunityCount(0);
      setHighSeverityCount(0);
      return;
    }
    fetchOpportunities(selectedProduct.id)
      .then((opps) => {
        setOpportunityCount(opps.length);
        setHighSeverityCount(opps.filter((o) => o.severity === 'High').length);
      })
      .catch(() => {
        setOpportunityCount(0);
        setHighSeverityCount(0);
      });
  }, [selectedProduct]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const insightCount = graphData?.nodes.filter((n) => n.node_type === 'Insight').length ?? 0;

  const handleShowEvidence = (nodeIds: string[], title: string) => {
    setDrawerNodeIds(nodeIds);
    setDrawerTitle(title);
    setDrawerOpen(true);
  };

  const handleOnboard = async () => {
    if (!onboardUrl.trim()) return;
    setOnboarding(true);
    try {
      const discovered = await onboardCompany(onboardUrl.trim());
      setShowOnboardModal(false);
      setOnboardUrl('');
      if (discovered.length > 0) {
        loadData();
      }
    } catch {
      // handled silently — user sees the modal stays open
    } finally {
      setOnboarding(false);
    }
  };

  const TAB_CONFIG: { key: ViewMode; label: string; icon: typeof Zap }[] = [
    { key: 'opportunities', label: 'Opportunities', icon: Zap },
    { key: 'personas', label: 'Personas', icon: Users },
    { key: 'research', label: 'Research', icon: Search },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar
        products={products}
        selectedProduct={selectedProduct}
        onSelectProduct={setSelectedProduct}
        onOnboard={() => setShowOnboardModal(true)}
      />

      <main
        style={{
          flex: 1,
          padding: '28px 32px',
          overflowY: 'auto',
          background:
            'radial-gradient(ellipse at top right, rgba(59, 130, 246, 0.04), transparent 60%), ' +
            'radial-gradient(ellipse at bottom left, rgba(139, 92, 246, 0.04), transparent 60%)',
        }}
      >
        {/* Top bar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 24,
          }}
        >
          <div>
            <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.03em' }}>
              {selectedProduct ? selectedProduct.name : (
                <span className="gradient-text">Chasm Dashboard</span>
              )}
            </h1>
            <p style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>
              {selectedProduct
                ? selectedProduct.description || 'Product feedback analysis'
                : 'AI-Powered Product Feedback Knowledge Graph'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Tab toggle */}
            <div
              style={{
                display: 'flex',
                borderRadius: 10,
                border: '1px solid #2a3154',
                overflow: 'hidden',
              }}
            >
              {TAB_CONFIG.map((tab, i) => (
                <button
                  key={tab.key}
                  onClick={() => setViewMode(tab.key)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    padding: '8px 14px',
                    border: 'none',
                    borderLeft: i > 0 ? '1px solid #2a3154' : 'none',
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 600,
                    transition: 'all 0.2s',
                    background: viewMode === tab.key
                      ? 'rgba(139, 92, 246, 0.2)'
                      : 'rgba(26, 31, 54, 0.5)',
                    color: viewMode === tab.key ? '#e2e8f0' : '#64748b',
                  }}
                >
                  <tab.icon size={13} />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Refresh */}
            <button
              onClick={loadData}
              disabled={loading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 16px',
                borderRadius: 10,
                border: '1px solid #2a3154',
                background: 'rgba(59, 130, 246, 0.08)',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 500,
                transition: 'all 0.2s',
              }}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div
            className="glass-card"
            style={{
              padding: '14px 20px',
              marginBottom: 20,
              borderColor: 'rgba(245, 158, 11, 0.3)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <span style={{ color: '#f59e0b', fontSize: 13 }}>{error}</span>
          </div>
        )}

        {/* Stats */}
        <StatsBar
          productCount={products.length}
          opportunityCount={opportunityCount}
          highSeverityCount={highSeverityCount}
          insightCount={insightCount}
        />

        {/* View content */}
        {viewMode === 'opportunities' && (
          <OpportunityFeed
            productId={selectedProduct?.id ?? null}
            onShowEvidence={handleShowEvidence}
          />
        )}

        {viewMode === 'personas' && (
          <PersonaExplorer
            productId={selectedProduct?.id ?? null}
            onShowEvidence={handleShowEvidence}
          />
        )}

        {viewMode === 'research' && (
          <GalaxyMap graphData={graphData} />
        )}
      </main>

      {/* Evidence Drawer */}
      {drawerOpen && (
        <EvidenceDrawer
          evidenceNodeIds={drawerNodeIds}
          title={drawerTitle}
          onClose={() => setDrawerOpen(false)}
        />
      )}

      {/* Onboard Modal */}
      {showOnboardModal && (
        <>
          <div
            onClick={() => setShowOnboardModal(false)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.6)',
              zIndex: 80,
            }}
          />
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 440,
              maxWidth: '90vw',
              background: 'linear-gradient(135deg, #1a1f36, #111827)',
              border: '1px solid #2a3154',
              borderRadius: 16,
              padding: '32px',
              zIndex: 85,
            }}
          >
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 }}>
              Onboard Company
            </h2>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>
              Enter a company website URL. Chasm will discover products automatically.
            </p>
            <input
              type="url"
              placeholder="https://example.com"
              value={onboardUrl}
              onChange={(e) => setOnboardUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleOnboard()}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 10,
                border: '1px solid #2a3154',
                background: 'rgba(10, 14, 26, 0.6)',
                color: '#e2e8f0',
                fontSize: 14,
                marginBottom: 16,
                outline: 'none',
              }}
              autoFocus
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowOnboardModal(false)}
                style={{
                  padding: '10px 20px',
                  borderRadius: 10,
                  border: '1px solid #2a3154',
                  background: 'transparent',
                  color: '#94a3b8',
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleOnboard}
                disabled={onboarding || !onboardUrl.trim()}
                style={{
                  padding: '10px 20px',
                  borderRadius: 10,
                  border: 'none',
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                  color: 'white',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: onboarding ? 'wait' : 'pointer',
                  opacity: !onboardUrl.trim() ? 0.5 : 1,
                }}
              >
                {onboarding ? 'Discovering...' : 'Discover Products'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
