import 'dart:async';
import 'dart:convert';
import 'dart:developer' as dev;

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/video_job.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);
  @override
  String toString() => 'ApiException($statusCode): $message';
}

/// Cliente HTTP del backend. Lee siempre `AppConfig.backendBaseUrl` para
/// que los cambios en Settings se reflejen sin recrear el servicio.
class ApiService {
  String get baseUrl => AppConfig.backendBaseUrl;

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  void _log(String s) {
    // Visible en `flutter run` y `flutter logs`; ignorado en release.
    dev.log(s, name: 'api');
  }

  // ───────────── Health / connectivity test ─────────────
  /// Devuelve {ok, latencyMs, data?, error?}. Nunca tira excepción.
  Future<Map<String, dynamic>> testConnection({Duration timeout = const Duration(seconds: 4)}) async {
    final stopwatch = Stopwatch()..start();
    final url = _u('/health');
    _log('GET $url');
    try {
      final r = await http.get(url).timeout(timeout);
      stopwatch.stop();
      _log('GET $url → ${r.statusCode} (${stopwatch.elapsedMilliseconds} ms)');
      if (r.statusCode != 200) {
        return {
          'ok': false,
          'latencyMs': stopwatch.elapsedMilliseconds,
          'error': 'HTTP ${r.statusCode}: ${r.body}',
        };
      }
      return {
        'ok': true,
        'latencyMs': stopwatch.elapsedMilliseconds,
        'data': jsonDecode(r.body),
      };
    } catch (e) {
      stopwatch.stop();
      _log('GET $url ✗ $e');
      return {
        'ok': false,
        'latencyMs': stopwatch.elapsedMilliseconds,
        'error': e.toString(),
      };
    }
  }

  // ───────────── Create job (multi-escena) ─────────────
  /// Crea un job con N escenas. Cada escena que tenga `referenceImage`
  /// se manda como `scene_image_<idx>` en el multipart.
  Future<String> createJob({
    required String title,
    required List<SceneInput> scenes,
    required int durationSeconds,
    String aspectRatio = '9:16',
    bool generateVoice = true,
    bool generateVideo = true,
    String? voiceId,
    String? style,
    bool musicEnabled = false,
    void Function(double progress)? onUploadProgress,
  }) async {
    if (scenes.isEmpty) {
      throw ApiException(0, 'Necesitás al menos una escena');
    }

    final url = _u('/jobs');
    _log('POST $url scenes=${scenes.length} '
        'voice=$generateVoice video=$generateVideo dur=${durationSeconds}s');

    final req = http.MultipartRequest('POST', url);
    req.fields['title'] = title;
    req.fields['duration_seconds'] = durationSeconds.toString();
    req.fields['aspect_ratio'] = aspectRatio;
    req.fields['generate_voice'] = generateVoice.toString();
    req.fields['generate_video'] = generateVideo.toString();
    req.fields['music_enabled'] = musicEnabled.toString();
    if (voiceId != null && voiceId.isNotEmpty) req.fields['voice_id'] = voiceId;
    if (style != null && style.isNotEmpty) req.fields['style'] = style;

    final scenesJson = scenes.map((s) => s.toJsonMetadata()).toList();
    req.fields['scenes'] = jsonEncode(scenesJson);

    for (int i = 0; i < scenes.length; i++) {
      final f = scenes[i].referenceImage;
      if (f == null) continue;
      _log('  attach scene_image_$i → ${f.path}');
      req.files.add(await http.MultipartFile.fromPath('scene_image_$i', f.path));
    }

    try {
      final streamed = await req.send().timeout(const Duration(seconds: 60));
      final r = await http.Response.fromStream(streamed);
      _log('POST $url → ${r.statusCode}');
      if (r.statusCode != 200) {
        throw ApiException(r.statusCode, r.body);
      }
      final data = jsonDecode(r.body) as Map<String, dynamic>;
      return data['job_id'] as String;
    } on TimeoutException {
      throw ApiException(0, 'Timeout: el backend no respondió en 60s. '
          '¿Está corriendo en $baseUrl?');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(0, 'Error de conexión a $baseUrl: $e');
    }
  }

  // ───────────── Job state / logs ─────────────
  Future<VideoJob> getJob(String jobId) async {
    final r = await http.get(_u('/jobs/$jobId'));
    if (r.statusCode != 200) throw ApiException(r.statusCode, r.body);
    return VideoJob.fromJson(jsonDecode(utf8.decode(r.bodyBytes)));
  }

  Future<String> getLogs(String jobId) async {
    final r = await http.get(_u('/jobs/$jobId/logs'));
    if (r.statusCode != 200) throw ApiException(r.statusCode, r.body);
    return utf8.decode(r.bodyBytes);
  }

  Future<List<JobSummary>> listJobs({int limit = 50}) async {
    final r = await http.get(_u('/jobs?limit=$limit'));
    if (r.statusCode != 200) throw ApiException(r.statusCode, r.body);
    final list = jsonDecode(utf8.decode(r.bodyBytes)) as List;
    return list.cast<Map<String, dynamic>>().map(JobSummary.fromJson).toList();
  }

  String downloadUrl(String jobId) => '$baseUrl/jobs/$jobId/download';
}
