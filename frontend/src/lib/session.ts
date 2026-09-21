/**
 * Tab and portal-scoped session management for PolicyPilot.
 * Enables Customer and Employee sessions to coexist independently in different tabs
 * on the same origin without cookie collision or silent cross-portal redirection.
 */

export type PortalType = 'employee' | 'customer' | 'admin' | 'neutral';

export function getPortalScope(pathname?: string): PortalType {
  const path = pathname || (typeof window !== 'undefined' ? window.location.pathname : '');

  if (path.startsWith('/employee')) {
    return 'employee';
  }
  if (path.startsWith('/admin')) {
    return 'admin';
  }
  if (path.startsWith('/dashboard')) {
    return 'customer';
  }

  if (typeof window !== 'undefined') {
    // If this tab already has an active tab session, use its authenticated role!
    const tabRole = sessionStorage.getItem('portal_role');
    if (tabRole === 'EMPLOYEE') return 'employee';
    if (tabRole === 'ADMIN') return 'admin';
    if (tabRole === 'CUSTOMER') return 'customer';

    // Explicit portal query parameter has priority for unauthenticated public routes (e.g. /login?portal=employee)
    const params = new URLSearchParams(window.location.search);
    const portalParam = params.get('portal');
    if (portalParam === 'employee') return 'employee';
    if (portalParam === 'admin') return 'admin';
    if (portalParam === 'customer') return 'customer';
  }

  // Public/neutral routes: /login, /register, /forgot-password, /reset-password, /
  return 'neutral';
}

export function getActiveSessionToken(pathname?: string): string | null {
  if (typeof window === 'undefined') return null;

  const currentPortal = getPortalScope(pathname);
  const tabToken = sessionStorage.getItem('session_token');
  const tabRole = sessionStorage.getItem('portal_role');

  if (currentPortal === 'employee') {
    // 1. Current tab has verified employee token
    if (tabToken && tabRole === 'EMPLOYEE') {
      return tabToken;
    }
    // 2. Portal-scoped employee fallback from localStorage (e.g. opened new employee tab)
    if (!tabToken || tabRole === 'EMPLOYEE') {
      const empToken = localStorage.getItem('employee_session_token');
      if (empToken) {
        sessionStorage.setItem('session_token', empToken);
        sessionStorage.setItem('portal_role', 'EMPLOYEE');
        return empToken;
      }
    }
    // 3. Never return a customer token or generic fallback on employee routes
    return null;
  }

  if (currentPortal === 'customer') {
    // 1. Current tab has verified customer token
    if (tabToken && (tabRole === 'CUSTOMER' || !tabRole)) {
      return tabToken;
    }
    // CRITICAL: If tab already has an active EMPLOYEE session, DO NOT overwrite it with customer token!
    if (tabToken && tabRole === 'EMPLOYEE') {
      return null;
    }
    // 2. Portal-scoped customer fallback from localStorage (e.g. opened new customer tab)
    if (!tabToken) {
      const custToken = localStorage.getItem('customer_session_token');
      if (custToken) {
        sessionStorage.setItem('session_token', custToken);
        sessionStorage.setItem('portal_role', 'CUSTOMER');
        return custToken;
      }
    }
    // 3. Never return an employee token or generic fallback on customer routes
    return null;
  }

  if (currentPortal === 'admin') {
    if (tabToken && tabRole === 'ADMIN') {
      return tabToken;
    }
    if (!tabToken || tabRole === 'ADMIN') {
      const adminToken = localStorage.getItem('admin_session_token');
      if (adminToken) {
        sessionStorage.setItem('session_token', adminToken);
        sessionStorage.setItem('portal_role', 'ADMIN');
        return adminToken;
      }
    }
    return null;
  }

  // Neutral routes (/login, /register, /, etc.):
  // If the current tab has an active token, return it
  if (tabToken) {
    return tabToken;
  }

  // On neutral routes without tab session, do not auto-inject localStorage token.
  // This allows clean login without premature redirection.
  return null;
}

export function setActiveSessionToken(token: string, role?: string, pathname?: string): void {
  if (typeof window === 'undefined') return;

  const portal = role === 'EMPLOYEE' 
    ? 'employee' 
    : (role === 'ADMIN' 
      ? 'admin' 
      : (role === 'CUSTOMER' 
        ? 'customer' 
        : getPortalScope(pathname)));

  sessionStorage.setItem('session_token', token);
  if (role) {
    sessionStorage.setItem('portal_role', role);
  } else {
    sessionStorage.setItem('portal_role', portal === 'employee' ? 'EMPLOYEE' : (portal === 'admin' ? 'ADMIN' : 'CUSTOMER'));
  }

  if (portal === 'employee' || role === 'EMPLOYEE') {
    localStorage.setItem('employee_session_token', token);
  } else if (portal === 'admin' || role === 'ADMIN') {
    localStorage.setItem('admin_session_token', token);
  } else {
    localStorage.setItem('customer_session_token', token);
  }
}

export function clearActiveSessionToken(pathname?: string): void {
  if (typeof window === 'undefined') return;

  const currentRole = sessionStorage.getItem('portal_role');
  const portal = getPortalScope(pathname);

  sessionStorage.removeItem('session_token');
  sessionStorage.removeItem('portal_role');

  if (portal === 'employee' || currentRole === 'EMPLOYEE') {
    localStorage.removeItem('employee_session_token');
  } else if (portal === 'admin' || currentRole === 'ADMIN') {
    localStorage.removeItem('admin_session_token');
  } else {
    localStorage.removeItem('customer_session_token');
  }
}

/**
 * Returns auth headers object for explicit use if needed.
 */
export function getAuthHeaders(pathname?: string): HeadersInit {
  const token = getActiveSessionToken(pathname);
  const portal = getPortalScope(pathname);
  const headers: Record<string, string> = {};

  if (portal !== 'neutral') {
    headers['X-Portal-Scope'] = portal;
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-Session-ID'] = token;
  }
  return headers;
}

/**
 * Installs global fetch interceptor to attach Authorization: Bearer <session_token>
 * and X-Portal-Scope on requests heading to the backend.
 */
export function setupFetchInterceptor(): void {
  if (typeof window === 'undefined') return;
  if ((window as any).__pp_fetch_interceptor_installed__) return;
  (window as any).__pp_fetch_interceptor_installed__ = true;

  const originalFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    try {
      const urlStr = typeof input === 'string' 
        ? input 
        : (input instanceof URL ? input.toString() : (input instanceof Request ? input.url : ''));
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      const isBackendRequest = 
        urlStr.startsWith(apiUrl) || 
        urlStr.startsWith('http://127.0.0.1:8000') || 
        urlStr.startsWith('http://localhost:8000') ||
        urlStr.startsWith('/api/') ||
        urlStr.startsWith('/auth/');

      if (isBackendRequest) {
        const portal = getPortalScope();
        const token = getActiveSessionToken();

        let headers: Headers;
        if (input instanceof Request) {
          headers = new Headers(input.headers);
          if (init?.headers) {
            new Headers(init.headers).forEach((v, k) => headers.set(k, v));
          }
        } else {
          headers = new Headers(init?.headers || {});
        }

        if (portal !== 'neutral' && !headers.has('X-Portal-Scope')) {
          headers.set('X-Portal-Scope', portal);
        }

        if (token) {
          if (!headers.has('Authorization')) {
            headers.set('Authorization', `Bearer ${token}`);
          }
          if (!headers.has('X-Session-ID')) {
            headers.set('X-Session-ID', token);
          }
        }

        const newInit: RequestInit = {
          ...init,
          headers,
          credentials: init?.credentials || 'include',
        };

        return originalFetch(input, newInit);
      }
    } catch (e) {
      console.warn('[Session] Fetch interceptor error:', e);
    }

    return originalFetch(input, init);
  };
}

// Auto-run on client evaluation
if (typeof window !== 'undefined') {
  setupFetchInterceptor();
}
