import { useState } from 'react';
import {
    LayoutDashboard,
    Box,
    ChevronRight,
    Radio,
    Zap,
    Plus,
} from 'lucide-react';
import type { ProductNode } from '../api';

interface SidebarProps {
    products: ProductNode[];
    selectedProduct: ProductNode | null;
    onSelectProduct: (product: ProductNode) => void;
    onOnboard: () => void;
}

export default function Sidebar({
    products,
    selectedProduct,
    onSelectProduct,
    onOnboard,
}: SidebarProps) {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <aside
            style={{
                width: collapsed ? 64 : 280,
                minHeight: '100vh',
                background: 'linear-gradient(180deg, #0f1629 0%, #0a0e1a 100%)',
                borderRight: '1px solid #1e2547',
                display: 'flex',
                flexDirection: 'column',
                transition: 'width 0.3s ease',
                overflow: 'hidden',
                flexShrink: 0,
            }}
        >
            {/* Logo */}
            <div
                style={{
                    padding: collapsed ? '20px 12px' : '20px 20px',
                    borderBottom: '1px solid #1e2547',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    cursor: 'pointer',
                }}
                onClick={() => setCollapsed(!collapsed)}
            >
                <div
                    style={{
                        width: 36,
                        height: 36,
                        borderRadius: 10,
                        background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                    }}
                >
                    <Zap size={18} color="white" />
                </div>
                {!collapsed && (
                    <div>
                        <div style={{ fontWeight: 700, fontSize: 18, letterSpacing: '-0.02em' }}>
                            <span className="gradient-text">Chasm</span>
                        </div>
                        <div style={{ fontSize: 10, color: '#64748b', fontWeight: 500, letterSpacing: '0.05em' }}>
                            KNOWLEDGE GRAPH
                        </div>
                    </div>
                )}
            </div>

            {/* Nav section */}
            <nav style={{ padding: collapsed ? '12px 8px' : '16px 12px', flex: 1 }}>
                {/* Dashboard link */}
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '10px 12px',
                        borderRadius: 10,
                        color: '#94a3b8',
                        cursor: 'pointer',
                        marginBottom: 4,
                        transition: 'all 0.2s',
                        background: !selectedProduct ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                    }}
                    onClick={() => onSelectProduct(null as any)}
                >
                    <LayoutDashboard size={18} />
                    {!collapsed && <span style={{ fontSize: 14, fontWeight: 500 }}>Dashboard</span>}
                </div>

                {/* Products header */}
                {!collapsed && (
                    <div
                        style={{
                            fontSize: 10,
                            fontWeight: 600,
                            color: '#475569',
                            letterSpacing: '0.1em',
                            padding: '16px 12px 8px',
                            textTransform: 'uppercase',
                        }}
                    >
                        Products
                    </div>
                )}

                {/* Product list */}
                {products.map((product) => {
                    const isActive = selectedProduct?.id === product.id;
                    return (
                        <div
                            key={product.id}
                            onClick={() => onSelectProduct(product)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 10,
                                padding: '10px 12px',
                                borderRadius: 10,
                                cursor: 'pointer',
                                marginBottom: 2,
                                background: isActive ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
                                borderLeft: isActive ? '3px solid #3b82f6' : '3px solid transparent',
                                transition: 'all 0.2s',
                            }}
                        >
                            <Box size={16} color={isActive ? '#3b82f6' : '#64748b'} />
                            {!collapsed && (
                                <>
                                    <span
                                        style={{
                                            fontSize: 13,
                                            fontWeight: isActive ? 600 : 400,
                                            color: isActive ? '#e2e8f0' : '#94a3b8',
                                            flex: 1,
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                        }}
                                    >
                                        {product.name}
                                    </span>
                                    {isActive && <ChevronRight size={14} color="#3b82f6" />}
                                </>
                            )}
                        </div>
                    );
                })}

                {/* Onboard button */}
                <div
                    onClick={onOnboard}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '10px 12px',
                        borderRadius: 10,
                        cursor: 'pointer',
                        marginTop: 8,
                        border: '1px dashed #2a3154',
                        color: '#64748b',
                        transition: 'all 0.2s',
                    }}
                >
                    <Plus size={16} />
                    {!collapsed && <span style={{ fontSize: 13 }}>Onboard Company</span>}
                </div>
            </nav>

            {/* Status footer */}
            <div
                style={{
                    padding: collapsed ? '12px 8px' : '16px 20px',
                    borderTop: '1px solid #1e2547',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Radio size={12} color="#10b981" className="pulse-glow" style={{ borderRadius: '50%' }} />
                    {!collapsed && (
                        <span style={{ fontSize: 11, color: '#64748b' }}>System Online</span>
                    )}
                </div>
            </div>
        </aside>
    );
}
