import React, { useState, useEffect, useCallback } from 'react';

const API_URL = "http://127.0.0.1:8000";

// ─── Estado global del access token (en memoria, no en localStorage) ──────────
// Siguiendo el patrón del ejemplo 05: el access token NUNCA se persiste en disco.
let accessTokenEnMemoria = null;

function getAccessToken() { return accessTokenEnMemoria; }
function setAccessToken(token) { accessTokenEnMemoria = token; }
function clearAccessToken() { accessTokenEnMemoria = null; }

// ─── Helpers de fetch con auth ────────────────────────────────────────────────

async function fetchConAuth(url, opciones = {}) {
    const token = getAccessToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(opciones.headers || {}),
    };
    return fetch(url, { ...opciones, headers, credentials: 'include' });
}

async function renovarAccessToken() {
    /**
     * Intenta renovar el access token usando el refresh token (cookie HttpOnly).
     * Si el refresh expiró o no existe, devuelve null.
     */
    try {
        const resp = await fetch(`${API_URL}/api/v1/auth/refresh`, {
            method: 'POST',
            credentials: 'include',
        });
        if (!resp.ok) return null;
        const data = await resp.json();
        setAccessToken(data.access_token);
        return data.access_token;
    } catch {
        return null;
    }
}

// ─── Componente principal ─────────────────────────────────────────────────────

export default function IslaInscripcion({ idActividad }) {
    const [vista, setVista] = useState('cargando'); // 'cargando' | 'login' | 'registrar' | 'inscripcion'
    const [participante, setParticipante] = useState(null);
    const [inscripto, setInscripto] = useState(false);
    const [error, setError] = useState(null);
    const [exito, setExito] = useState(null);
    const [procesando, setProcesando] = useState(false);

    // Formularios
    const [formLogin, setFormLogin] = useState({ email: '', contrasena: '' });
    const [formReg, setFormReg] = useState({ nombre: '', email: '', contrasena: '' });

    // ─── Inicialización: intentar renovar el token al cargar ─────────────────
    useEffect(() => {
        (async () => {
            // Si ya hay un access token en memoria, usarlo directamente
            if (getAccessToken()) {
                await cargarPerfil();
                return;
            }
            // Intentar renovar desde la cookie HttpOnly
            const token = await renovarAccessToken();
            if (token) {
                await cargarPerfil();
            } else {
                setVista('login');
            }
        })();
    }, []);

    const cargarPerfil = useCallback(async () => {
        try {
            const resp = await fetchConAuth(`${API_URL}/api/v1/me`);
            if (resp.status === 401) {
                // Token expirado: intentar renovar
                const nuevo = await renovarAccessToken();
                if (!nuevo) { clearAccessToken(); setVista('login'); return; }
                const resp2 = await fetchConAuth(`${API_URL}/api/v1/me`);
                if (!resp2.ok) { clearAccessToken(); setVista('login'); return; }
                const data = await resp2.json();
                setParticipante(data);
            } else if (resp.ok) {
                const data = await resp.json();
                setParticipante(data);
            } else {
                setVista('login'); return;
            }
            await verificarInscripcion();
            setVista('inscripcion');
        } catch {
            setVista('login');
        }
    }, [idActividad]);

    const verificarInscripcion = useCallback(async () => {
        try {
            const resp = await fetchConAuth(`${API_URL}/api/v1/me/enrollments`);
            if (!resp.ok) return;
            const inscripciones = await resp.json();
            const estaInscripto = inscripciones.some(
                (i) => i.id_actividad === parseInt(idActividad)
            );
            setInscripto(estaInscripto);
        } catch { /* ignorar */ }
    }, [idActividad]);

    // ─── Login ────────────────────────────────────────────────────────────────
    const manejarLogin = async (e) => {
        e.preventDefault();
        setProcesando(true);
        setError(null);
        try {
            const resp = await fetch(`${API_URL}/api/v1/auth/login`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formLogin),
            });
            const data = await resp.json();
            if (!resp.ok) {
                setError(data.mensaje || 'Credenciales incorrectas.');
                return;
            }
            setAccessToken(data.access_token);
            setParticipante(data.participante);
            await verificarInscripcion();
            setVista('inscripcion');
        } catch {
            setError('Error de red. Verificá que el servidor esté activo.');
        } finally {
            setProcesando(false);
        }
    };

    // ─── Registro ─────────────────────────────────────────────────────────────
    const manejarRegistro = async (e) => {
        e.preventDefault();
        setProcesando(true);
        setError(null);
        try {
            const resp = await fetch(`${API_URL}/api/v1/auth/register`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formReg),
            });
            const data = await resp.json();
            if (!resp.ok) {
                setError(data.mensaje || 'Error al registrarse.');
                return;
            }
            // Auto-login después del registro
            setFormLogin({ email: formReg.email, contrasena: formReg.contrasena });
            setExito('¡Cuenta creada! Iniciando sesión...');
            setTimeout(() => {
                setExito(null);
                setVista('login');
            }, 1200);
        } catch {
            setError('Error de red.');
        } finally {
            setProcesando(false);
        }
    };

    // ─── Logout ───────────────────────────────────────────────────────────────
    const manejarLogout = async () => {
        await fetch(`${API_URL}/api/v1/auth/logout`, {
            method: 'POST',
            credentials: 'include',
        });
        clearAccessToken();
        setParticipante(null);
        setInscripto(false);
        setError(null);
        setVista('login');
    };

    // ─── Inscripción ──────────────────────────────────────────────────────────
    const manejarInscripcion = async (e) => {
        e.preventDefault();
        setProcesando(true);
        setError(null);
        setExito(null);
        try {
            let resp = await fetchConAuth(`${API_URL}/api/v1/me/enrollments/${idActividad}`, { method: 'PUT' });
            // Si el access expiró, renovar y reintentar
            if (resp.status === 401) {
                const nuevo = await renovarAccessToken();
                if (!nuevo) { clearAccessToken(); setVista('login'); return; }
                resp = await fetchConAuth(`${API_URL}/api/v1/me/enrollments/${idActividad}`, { method: 'PUT' });
            }
            const data = await resp.json();
            if (resp.status === 201) {
                setExito('¡Inscripción registrada con éxito!');
                setInscripto(true);
            } else if (resp.status === 409) {
                setError(data.mensaje || 'Ya estás inscripto o no hay cupo.');
            } else {
                setError(data.mensaje || `Error ${resp.status}`);
            }
        } catch {
            setError('Error de red.');
        } finally {
            setProcesando(false);
        }
    };

    // ─── Cancelar inscripción ─────────────────────────────────────────────────
    const manejarCancelacion = async () => {
        setProcesando(true);
        setError(null);
        setExito(null);
        try {
            let resp = await fetchConAuth(
                `${API_URL}/api/v1/me/enrollments/${idActividad}/cancel`,
                { method: 'DELETE' }
            );
            if (resp.status === 401) {
                const nuevo = await renovarAccessToken();
                if (!nuevo) { clearAccessToken(); setVista('login'); return; }
                resp = await fetchConAuth(
                    `${API_URL}/api/v1/me/enrollments/${idActividad}/cancel`,
                    { method: 'DELETE' }
                );
            }
            const data = await resp.json();
            if (resp.ok) {
                setExito('Inscripción cancelada.');
                setInscripto(false);
            } else {
                setError(data.mensaje || `Error ${resp.status}`);
            }
        } catch {
            setError('Error de red.');
        } finally {
            setProcesando(false);
        }
    };

    // ─── Render ───────────────────────────────────────────────────────────────

    const estiloContenedor = {
        marginTop: '2rem',
        padding: '1.75rem 2rem',
        background: 'linear-gradient(135deg, #f8fafc 0%, #ffffff 100%)',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
        fontFamily: 'system-ui, -apple-system, sans-serif',
    };

    const estiloBoton = (color = '#3b82f6', disabled = false) => ({
        padding: '0.65rem 1.4rem',
        background: disabled ? '#94a3b8' : color,
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontWeight: '600',
        fontSize: '0.95rem',
        transition: 'background 0.2s, transform 0.1s',
        boxShadow: disabled ? 'none' : '0 2px 6px rgba(0,0,0,0.15)',
    });

    const estiloInput = {
        padding: '0.6rem 0.85rem',
        width: '100%',
        maxWidth: '320px',
        borderRadius: '7px',
        border: '1.5px solid #cbd5e1',
        fontSize: '0.95rem',
        outline: 'none',
        boxSizing: 'border-box',
        marginTop: '0.3rem',
    };

    const estiloLabel = {
        display: 'block',
        fontWeight: '600',
        color: '#475569',
        marginBottom: '0.1rem',
        fontSize: '0.9rem',
    };

    const estiloAlerta = (tipo) => ({
        padding: '0.85rem 1rem',
        borderRadius: '8px',
        marginBottom: '1rem',
        fontSize: '0.9rem',
        borderLeft: `4px solid ${tipo === 'error' ? '#ef4444' : '#22c55e'}`,
        background: tipo === 'error' ? '#fef2f2' : '#f0fdf4',
        color: tipo === 'error' ? '#b91c1c' : '#166534',
    });

    if (vista === 'cargando') {
        return (
            <div style={estiloContenedor}>
                <p style={{ color: '#64748b', textAlign: 'center' }}>⏳ Verificando sesión...</p>
            </div>
        );
    }

    return (
        <div style={estiloContenedor}>
            {/* Header con info del usuario */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1.5px solid #e2e8f0', paddingBottom: '0.85rem', marginBottom: '1.25rem' }}>
                <h3 style={{ margin: 0, color: '#1e293b', fontSize: '1.1rem' }}>
                    {vista === 'inscripcion' ? '🎫 Gestión de Inscripción' : vista === 'login' ? '🔑 Iniciar sesión' : '📝 Crear cuenta'}
                </h3>
                {vista === 'inscripcion' && participante && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
                            Hola, <strong>{participante.nombre}</strong>
                        </span>
                        <button onClick={manejarLogout} style={{ ...estiloBoton('#64748b'), padding: '0.4rem 0.85rem', fontSize: '0.82rem' }}>
                            Salir
                        </button>
                    </div>
                )}
            </div>

            {/* Alertas */}
            {error && <div style={estiloAlerta('error')}><strong>Error:</strong> {error}</div>}
            {exito && <div style={estiloAlerta('exito')}>{exito}</div>}

            {/* ── Vista: Login ── */}
            {vista === 'login' && (
                <form onSubmit={manejarLogin}>
                    <p style={{ margin: '0 0 1.1rem 0', color: '#475569', fontSize: '0.9rem' }}>
                        Iniciá sesión para inscribirte. El token se guarda solo en memoria.
                    </p>
                    <div style={{ marginBottom: '0.85rem' }}>
                        <label style={estiloLabel}>Email</label>
                        <input
                            id="login-email"
                            type="email"
                            required
                            value={formLogin.email}
                            onChange={(e) => setFormLogin({ ...formLogin, email: e.target.value })}
                            placeholder="ana@example.com"
                            style={estiloInput}
                        />
                    </div>
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={estiloLabel}>Contraseña</label>
                        <input
                            id="login-password"
                            type="password"
                            required
                            value={formLogin.contrasena}
                            onChange={(e) => setFormLogin({ ...formLogin, contrasena: e.target.value })}
                            placeholder="••••••••"
                            style={estiloInput}
                        />
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <button id="btn-login" type="submit" disabled={procesando} style={estiloBoton('#3b82f6', procesando)}>
                            {procesando ? 'Ingresando...' : 'Iniciar sesión'}
                        </button>
                        <button type="button" onClick={() => { setVista('registrar'); setError(null); }}
                            style={{ background: 'none', border: 'none', color: '#3b82f6', cursor: 'pointer', fontSize: '0.9rem', textDecoration: 'underline' }}>
                            ¿No tenés cuenta? Registrate
                        </button>
                    </div>
                </form>
            )}

            {/* ── Vista: Registro ── */}
            {vista === 'registrar' && (
                <form onSubmit={manejarRegistro}>
                    <div style={{ marginBottom: '0.85rem' }}>
                        <label style={estiloLabel}>Nombre completo</label>
                        <input
                            id="reg-nombre"
                            type="text"
                            required
                            value={formReg.nombre}
                            onChange={(e) => setFormReg({ ...formReg, nombre: e.target.value })}
                            placeholder="Tu nombre"
                            style={estiloInput}
                        />
                    </div>
                    <div style={{ marginBottom: '0.85rem' }}>
                        <label style={estiloLabel}>Email</label>
                        <input
                            id="reg-email"
                            type="email"
                            required
                            value={formReg.email}
                            onChange={(e) => setFormReg({ ...formReg, email: e.target.value })}
                            placeholder="tu@email.com"
                            style={estiloInput}
                        />
                    </div>
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label style={estiloLabel}>Contraseña</label>
                        <input
                            id="reg-password"
                            type="password"
                            required
                            value={formReg.contrasena}
                            onChange={(e) => setFormReg({ ...formReg, contrasena: e.target.value })}
                            placeholder="Mínimo 8 caracteres"
                            style={estiloInput}
                        />
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <button id="btn-registrar" type="submit" disabled={procesando} style={estiloBoton('#10b981', procesando)}>
                            {procesando ? 'Registrando...' : 'Crear cuenta'}
                        </button>
                        <button type="button" onClick={() => { setVista('login'); setError(null); }}
                            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '0.9rem', textDecoration: 'underline' }}>
                            ← Volver al login
                        </button>
                    </div>
                </form>
            )}

            {/* ── Vista: Inscripción ── */}
            {vista === 'inscripcion' && (
                <div>
                    {inscripto ? (
                        <div>
                            <div style={{ padding: '1rem', background: '#f0fdf4', borderRadius: '8px', borderLeft: '4px solid #22c55e', marginBottom: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ fontSize: '1.2rem' }}>✓</span>
                                <strong style={{ color: '#166534' }}>Ya estás inscripto a esta actividad.</strong>
                            </div>
                            <button
                                id="btn-cancelar"
                                onClick={manejarCancelacion}
                                disabled={procesando}
                                style={estiloBoton('#ef4444', procesando)}
                            >
                                {procesando ? 'Procesando...' : 'Cancelar inscripción'}
                            </button>
                        </div>
                    ) : (
                        <div>
                            <p style={{ color: '#475569', marginBottom: '1.1rem' }}>
                                Actualmente <strong>no</strong> estás inscripto. ¿Deseás participar en esta actividad?
                            </p>
                            <button
                                id="btn-inscribir"
                                onClick={manejarInscripcion}
                                disabled={procesando}
                                style={estiloBoton('#10b981', procesando)}
                            >
                                {procesando ? 'Procesando...' : 'Confirmar inscripción'}
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
