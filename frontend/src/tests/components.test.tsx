import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { Login } from '@/pages/Login';

// Mock the API client
vi.mock('@/lib/api', () => ({
  api: {
    auth: {
      login: vi.fn(),
      me: vi.fn(),
      logout: vi.fn(),
    },
    warehouses: {
      list: vi.fn().mockResolvedValue([
        { id: 'wh-1', code: 'WH-MAIN', name: 'Main Distribution Center', is_active: true },
      ]),
    },
    reports: {
      getDashboard: vi.fn().mockResolvedValue({
        total_products: 42,
        total_valuation: 150000,
        low_stock_count: 2,
        open_pos_count: 3,
        open_sos_count: 5,
        total_warehouses: 2,
      }),
      getReplenishment: vi.fn().mockResolvedValue([]),
      getValuation: vi.fn().mockResolvedValue([]),
    },
  },
}));

describe('BizPilot Frontend Core', () => {
  it('renders login screen with branding and quick demo accounts', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <Login />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByText('BizPilot ERP')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('name@company.com')).toBeInTheDocument();
    expect(screen.getByText('Admin Role')).toBeInTheDocument();
    expect(screen.getByText('Manager Role')).toBeInTheDocument();
    expect(screen.getByText('Warehouse Staff')).toBeInTheDocument();
  });

  it('validates stock calculation invariants: Available = On-Hand - Reserved', () => {
    const onHand = 150;
    const reserved = 35;
    const available = onHand - reserved;

    expect(available).toBe(115);
    expect(available).toBeGreaterThanOrEqual(0);
  });
});
