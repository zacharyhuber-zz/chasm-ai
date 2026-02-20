import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Target, Orbit } from 'lucide-react';
import Sidebar from './components/Sidebar';
import AlignmentMatrix from './components/AlignmentMatrix';
import GalaxyMap from './components/GalaxyMap';
import StatsBar from './components/StatsBar';
import {
  fetchProducts,
  fetchGraph,
  deriveComponentSentiments,
  type ProductNode,
  type GraphData,
  type ComponentSentiment,
} from './api';

type ViewMode = 'matrix' | 'galaxy';

export default function App() {
  const [products, setProducts] = useState<ProductNode[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<ProductNode | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [sentiments, setSentiments] = useState<ComponentSentiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('matrix');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [prods, graph] = await Promise.all([fetchProducts(), fetchGraph()]);
      setProducts(prods);
      setGraphData(graph);
      setSentiments(deriveComponentSentiments(graph));
    } catch {
      setError('Could not connect to Chasm API. Is the backend running on port 8000?');
      setProducts([]);
      setGraphData({ nodes: [], links: [] });
      setSentiments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const nodeCount = graphData?.nodes.length ?? 0;
  const edgeCount = graphData?.links.length ?? 0;
  const insightCount = graphData?.nodes.filter((n) => n.node_type === 'Insight').length ?? 0;

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar
        products={products}
        selectedProduct={selectedProduct}
        onSelectProduct={setSelectedProduct}
        onOnboard={async () => {
          const url = prompt('Enter company URL to onboard:');
          if (url) {
            try {
              const { onboardCompany } = await import('./api');
              const discovered = await onboardCompany(url);
              alert(`Discovered ${discovered.length} product(s). Check the sidebar.`);
              loadData();
            } catch {
              alert('Onboarding failed. Is the backend running?');
            }
          }
        }}
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
                ? selectedProduct.description || 'Hardware feedback analysis'
                : 'AI-Powered Hardware Feedback Knowledge Graph'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* View toggle */}
            <div
              style={{
                display: 'flex',
                borderRadius: 10,
                border: '1px solid #2a3154',
                overflow: 'hidden',
              }}
            >
              <button
                onClick={() => setViewMode('matrix')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '8px 14px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                  transition: 'all 0.2s',
                  background: viewMode === 'matrix'
                    ? 'rgba(139, 92, 246, 0.2)'
                    : 'rgba(26, 31, 54, 0.5)',
                  color: viewMode === 'matrix' ? '#e2e8f0' : '#64748b',
                }}
              >
                <Target size={13} />
                Matrix
              </button>
              <button
                onClick={() => setViewMode('galaxy')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  padding: '8px 14px',
                  border: 'none',
                  borderLeft: '1px solid #2a3154',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                  transition: 'all 0.2s',
                  background: viewMode === 'galaxy'
                    ? 'rgba(59, 130, 246, 0.2)'
                    : 'rgba(26, 31, 54, 0.5)',
                  color: viewMode === 'galaxy' ? '#e2e8f0' : '#64748b',
                }}
              >
                <Orbit size={13} />
                Galaxy
              </button>
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
            <span style={{ fontSize: 18 }}>⚠️</span>
            <span style={{ color: '#f59e0b', fontSize: 13 }}>{error}</span>
          </div>
        )}

        {/* Stats */}
        <StatsBar
          nodeCount={nodeCount}
          edgeCount={edgeCount}
          productCount={products.length}
          insightCount={insightCount}
        />

        {/* View switcher */}
        {viewMode === 'matrix' ? (
          <>
            <AlignmentMatrix
              data={sentiments}
              productName={selectedProduct?.name ?? 'All Products'}
            />

            {/* Quick info */}
            <div
              className="glass-card fade-in"
              style={{
                padding: '20px 24px',
                marginTop: 20,
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 24,
              }}
            >
              {[
                {
                  title: 'How it Works',
                  desc: 'Components are plotted by comparing internal team sentiment against external user feedback.',
                },
                {
                  title: 'Blind Spot',
                  desc: 'Bottom-right quadrant: Your team thinks it\'s fine, but users are complaining. Investigate immediately.',
                },
                {
                  title: 'Over-Engineered',
                  desc: 'Top-left quadrant: Users love it, but your team rates it low. Reallocate resources elsewhere.',
                },
              ].map((item) => (
                <div key={item.title}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0', marginBottom: 6 }}>
                    {item.title}
                  </h3>
                  <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>{item.desc}</p>
                </div>
              ))}
            </div>
          </>
        ) : (
          <GalaxyMap graphData={graphData} />
        )}
      </main>
    </div>
  );
}
