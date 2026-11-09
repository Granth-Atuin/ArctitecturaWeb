"""Cliente gRPC de prueba para invocar el servicio de inscripciones desde Python."""

import json
import sys
import urllib.error
import urllib.request
import grpc

from actividades.grpc import inscripciones_pb2, inscripciones_pb2_grpc


def main():
    actividad_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    email = sys.argv[2] if len(sys.argv) > 2 else "ana@example.com"
    password = sys.argv[3] if len(sys.argv) > 3 else "Demo1234!"
    api_url = "http://127.0.0.1:8000/api/v1/auth/login"
    grpc_host = "127.0.0.1:50051"

    print(f"1. Solicitando Access Token JWT a {api_url} para {email}...")
    try:
        req_data = json.dumps({"email": email, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("access_token")
            print("✓ Token JWT obtenido con éxito.")
    except urllib.error.HTTPError as e:
        print(f"Error HTTP al autenticar ({e.code}): {e.read().decode('utf-8')}")
        return
    except Exception as e:
        print(f"No se pudo conectar a la API HTTP ({e}).")
        print("Asegurate de que el backend Django esté corriendo en el puerto 8000.")
        return

    print(f"\n2. Conectando al servidor gRPC en {grpc_host}...")
    canal = grpc.insecure_channel(grpc_host)
    stub = inscripciones_pb2_grpc.InscripcionesStub(canal)

    # Invocación con JWT Bearer en la metadata
    metadata = (("authorization", f"Bearer {token}"),)
    request = inscripciones_pb2.InscribirRequest(actividad_id=str(actividad_id))

    try:
        print(f"3. Invocando Inscribir(actividad_id='{actividad_id}')...")
        respuesta = stub.Inscribir(request, metadata=metadata)
        print("\n=== RESPUESTA gRPC EXITOSA ===")
        print(f"• Creada:          {respuesta.creada}")
        print(f"• Actividad ID:    {respuesta.actividad_id}")
        print(f"• Participante ID: {respuesta.participante_id}")
        print(f"• Inscripta en:    {respuesta.inscripta_en}")
        print("==============================")
    except grpc.RpcError as rpc_error:
        print("\n=== ERROR gRPC ===")
        print(f"• Código de estado: {rpc_error.code()}")
        print(f"• Detalle:          {rpc_error.details()}")
        print("==================")


if __name__ == "__main__":
    main()
