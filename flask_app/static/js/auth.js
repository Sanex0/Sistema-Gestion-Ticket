// ============================================
// MÓDULO DE AUTENTICACIÓN JWT
// ============================================

const AUTH_CONFIG = {
    API_BASE_URL: 'http://127.0.0.1:5000/api',
    TOKEN_KEY: 'access_token',
    REFRESH_TOKEN_KEY: 'refresh_token',
    USER_KEY: 'current_user'
};

class AuthService {
    static async login(email, password) {
        try {
            const response = await fetch(`${AUTH_CONFIG.API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            let data = null;
            try {
                data = await response.json();
            } catch (e) {
                data = null;
            }

            if (data && data.success) {
                // Guardar tokens y usuario en sessionStorage (único por pestaña)
                sessionStorage.setItem(AUTH_CONFIG.TOKEN_KEY, data.access_token);
                sessionStorage.setItem(AUTH_CONFIG.REFRESH_TOKEN_KEY, data.refresh_token);
                sessionStorage.setItem(AUTH_CONFIG.USER_KEY, JSON.stringify(data.operador));
                
                return { success: true, user: data.operador };
            } else {
                const errorMessage = (data && (data.error || data.message)) || 'Error en el login';
                const errorCode = (data && data.error_code) || null;
                return { success: false, error: errorMessage, code: errorCode, status: response.status };
            }
        } catch (error) {
            console.error('Error en login:', error);
            return { success: false, error: 'Error de conexión con el servidor' };
        }
    }

    static logout() {
        sessionStorage.removeItem(AUTH_CONFIG.TOKEN_KEY);
        sessionStorage.removeItem(AUTH_CONFIG.REFRESH_TOKEN_KEY);
        sessionStorage.removeItem(AUTH_CONFIG.USER_KEY);
        window.location.href = '/';
    }

    static getToken() {
        return sessionStorage.getItem(AUTH_CONFIG.TOKEN_KEY);
    }

    static getRefreshToken() {
        return sessionStorage.getItem(AUTH_CONFIG.REFRESH_TOKEN_KEY);
    }

    static getCurrentUser() {
        const userJson = sessionStorage.getItem(AUTH_CONFIG.USER_KEY);
        return userJson ? JSON.parse(userJson) : null;
    }

    static isAuthenticated() {
        return !!this.getToken();
    }

    static async refreshToken() {
        try {
            const refreshToken = this.getRefreshToken();
            if (!refreshToken) return false;

            const response = await fetch(`${AUTH_CONFIG.API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refreshToken}`
                }
            });

            const data = await response.json();

            if (data.success && data.access_token) {
                sessionStorage.setItem(AUTH_CONFIG.TOKEN_KEY, data.access_token);
                return true;
            }

            return false;
        } catch (error) {
            console.error('Error al refrescar token:', error);
            return false;
        }
    }

    static getAuthHeaders() {
        const token = this.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }
}

// ============================================
// WRAPPER FETCH CON AUTENTICACIÓN
// ============================================

async function apiRequest(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${AUTH_CONFIG.API_BASE_URL}${endpoint}`;
    
    const config = {
        ...options,
        headers: {
            ...AuthService.getAuthHeaders(),
            ...options.headers
        }
    };

    try {
        let response = await fetch(url, config);

        // Si es 401, intentar refrescar token y reintentar
        if (response.status === 401) {
            const refreshed = await AuthService.refreshToken();
            if (refreshed) {
                // Reintentar con nuevo token
                config.headers.Authorization = `Bearer ${AuthService.getToken()}`;
                response = await fetch(url, config);
            } else {
                // Token expirado, redirigir a login
                AuthService.logout();
                return null;
            }
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error en apiRequest:', error);
        throw error;
    }
}

// ============================================
// PROTECCIÓN DE RUTAS
// ============================================

function requireAuth() {
    if (!AuthService.isAuthenticated()) {
        window.location.href = '/';
        return false;
    }
    return true;
}

// Verificar autenticación al cargar página
if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
    requireAuth();
}
