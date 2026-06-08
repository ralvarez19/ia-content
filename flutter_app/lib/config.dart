/// Configuración del cliente: dónde vive el backend FastAPI.
///
/// - En la misma PC: http://127.0.0.1:8000
/// - Desde otro dispositivo en la misma red (uvicorn corriendo con
///   --host 0.0.0.0): http://<IP-de-tu-PC>:8000
class AppConfig {
  /// Cambia esta URL si vas a usar la app desde otro dispositivo en la LAN.
  static const String backendBaseUrl = 'http://127.0.0.1:8000';

  /// Intervalo (segundos) para hacer polling del estado del job.
  static const int progressPollSeconds = 2;
}
