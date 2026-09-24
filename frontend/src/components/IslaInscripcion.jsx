import React, { useState, useEffect } from 'react';

const API_URL = import.meta.env.PUBLIC_CLIENT_API_URL || "http://127.0.0.1:8000/api/v1";

export default function IslaInscripcion({ idActividad }) {
    const [cargando, setCargando] = useState(true);
    const [error, setError] = useState(null);
    const [inscripto, setInscripto] = useState(false);
    const [procesando, setProcesando] = useState(false);
    const [mensajeExito, setMensajeExito] = useState("");
    
    // Estado para simular la sesión (el participante actual)
    const [tokenUsuario, setTokenUsuario] = useState("");

    const consultarInscripcion = async () => {
        setCargando(true);
        setError(null);
        try {
            const respuesta = await fetch(`${API_URL}/me/enrollments`, {
                headers: {
                    'Authorization': tokenUsuario ? `Bearer ${tokenUsuario}` : ''
                }
            });

            if (respuesta.status === 401) {
                setError("Estado: No autenticado (401). Ingresa tu identificador para simular la sesión.");
                setCargando(false);
                return;
            }

            if (!respuesta.ok) {
                throw new Error("Error de servidor al consultar inscripciones");
            }

            const inscripciones = await respuesta.json();
            
            // Verificamos si en la lista de inscripciones del usuario actual está esta actividad
            const yaInscripto = inscripciones.some(
                (inscripcion) => inscripcion.id_actividad === parseInt(idActividad)
            );
            
            setInscripto(yaInscripto);
        } catch (err) {
            setError("Ocurrió un error de red: " + err.message);
        } finally {
            setCargando(false);
        }
    };

    // Consultamos el estado de inscripción al montar la isla y cuando cambie el "token"
    useEffect(() => {
        consultarInscripcion();
    }, [idActividad, tokenUsuario]);

    const manejarInscripcion = async (e) => {
        e.preventDefault();
        setProcesando(true);
        setError(null);
        setMensajeExito("");

        try {
            const respuesta = await fetch(`${API_URL}/me/enrollments/${idActividad}`, {
                method: 'PUT',
                headers: {
                    'Authorization': tokenUsuario ? `Bearer ${tokenUsuario}` : ''
                }
            });

            if (respuesta.status === 401) {
                setError("Error 401: No estás autenticado para realizar esta inscripción.");
                return;
            }

            if (respuesta.status === 409) {
                const data = await respuesta.json();
                setError(`Conflicto (409): ${data.error || 'Ya estás inscripto o no hay cupo.'}`);
                return;
            }

            if (respuesta.status === 200 || respuesta.status === 201) {
                setMensajeExito("¡Inscripción registrada con éxito!");
                setInscripto(true);
                return;
            }

            throw new Error(`Error de servidor (${respuesta.status})`);
        } catch (err) {
            setError(err.message);
        } finally {
            setProcesando(false);
        }
    };

    const manejarCambioUsuario = (e) => {
        setTokenUsuario(e.target.value);
    };

    return (
        <div style={{ marginTop: '3rem', padding: '1.5rem', backgroundColor: '#ffffff', border: '1px solid #e1e8ed', borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
            <h3 style={{ marginTop: 0, color: '#2c3e50', borderBottom: '2px solid #ecf0f1', paddingBottom: '0.5rem' }}>
                Gestión de Inscripción (Isla Interactiva)
            </h3>
            
            <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#34495e' }}>
                    Simular Sesión (Participante):
                </label>
                <input 
                    type="text" 
                    value={tokenUsuario}
                    onChange={manejarCambioUsuario}
                    placeholder="Ej: juan_perez"
                    style={{ padding: '0.65rem', width: '100%', maxWidth: '350px', borderRadius: '4px', border: '1px solid #bdc3c7', fontSize: '1rem' }}
                />
                <p style={{ fontSize: '0.85rem', color: '#7f8c8d', margin: '0.4rem 0 0 0' }}>
                    * Si dejas esto en blanco, el backend retornará error 401 al consultar o inscribirte.
                </p>
            </div>

            {cargando ? (
                <div style={{ display: 'flex', alignItems: 'center', color: '#2980b9', fontWeight: 'bold' }}>
                    <span style={{ marginRight: '8px' }}>⏳</span> Consultando...
                </div>
            ) : (
                <div>
                    {error && (
                        <div style={{ padding: '1rem', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '4px', marginBottom: '1.2rem', borderLeft: '4px solid #e74c3c' }}>
                            <strong>Aviso:</strong> {error}
                        </div>
                    )}
                    
                    {mensajeExito && (
                        <div style={{ padding: '1rem', backgroundColor: '#d4edda', color: '#155724', borderRadius: '4px', marginBottom: '1.2rem', borderLeft: '4px solid #2ecc71' }}>
                            {mensajeExito}
                        </div>
                    )}

                    {!error && inscripto && (
                        <div style={{ padding: '1rem', backgroundColor: '#e8f8f5', color: '#117a65', borderRadius: '4px', fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
                            <span style={{ fontSize: '1.2rem', marginRight: '8px' }}>✓</span> 
                            Ya te encuentras inscripto a esta actividad.
                        </div>
                    )}

                    {!inscripto && (
                        <form onSubmit={manejarInscripcion} style={{ marginTop: '1rem' }}>
                            <p style={{ marginBottom: '1rem', color: '#34495e' }}>Actualmente <strong>no</strong> estás inscripto. ¿Deseas participar en esta actividad?</p>
                            <button 
                                type="submit" 
                                disabled={procesando || !tokenUsuario}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    backgroundColor: procesando || !tokenUsuario ? '#95a5a6' : '#2ecc71',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: procesando || !tokenUsuario ? 'not-allowed' : 'pointer',
                                    fontWeight: 'bold',
                                    fontSize: '1rem',
                                    transition: 'background-color 0.2s',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                }}
                            >
                                {procesando ? 'Procesando solicitud...' : 'Confirmar Inscripción'}
                            </button>
                        </form>
                    )}
                </div>
            )}
        </div>
    );
}
