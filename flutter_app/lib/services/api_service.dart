import 'dart:async';
import 'dart:convert';
import 'dart:io';

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

class ApiService {
  ApiService({String? baseUrl}) : baseUrl = baseUrl ?? AppConfig.backendBaseUrl;
  final String baseUrl;

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  // ───────────── Health ─────────────
  Future<Map<String, dynamic>> health() async {
    final r = await http.get(_u('/health')).timeout(const Duration(seconds: 5));
    if (r.statusCode != 200) {
      throw ApiException(r.statusCode, r.body);
    }
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  // ───────────── Create job ─────────────
  Future<String> createJob({
    required String title,
    required String scene,
    required String dialogue,
    required int clipsCount,
    required int durationSeconds,
    String aspectRatio = '9:16',
    bool generateVoice = true,
    bool generateVideo = true,
    bool useReferenceImage = false,
    String? voiceId,
    String? style,
    bool musicEnabled = false,
    File? referenceImage,
  }) async {
    final req = http.MultipartRequest('POST', _u('/jobs'));
    req.fields['title'] = title;
    req.fields['scene'] = scene;
    req.fields['dialogue'] = dialogue;
    req.fields['clips_count'] = clipsCount.toString();
    req.fields['duration_seconds'] = durationSeconds.toString();
    req.fields['aspect_ratio'] = aspectRatio;
    req.fields['generate_voice'] = generateVoice.toString();
    req.fields['generate_video'] = generateVideo.toString();
    req.fields['use_reference_image'] = useReferenceImage.toString();
    if (voiceId != null && voiceId.isNotEmpty) req.fields['voice_id'] = voiceId;
    if (style != null && style.isNotEmpty) req.fields['style'] = style;
    req.fields['music_enabled'] = musicEnabled.toString();

    if (referenceImage != null) {
      req.files.add(await http.MultipartFile.fromPath(
        'reference_image',
        referenceImage.path,
      ));
    }

    final streamed = await req.send();
    final r = await http.Response.fromStream(streamed);
    if (r.statusCode != 200) {
      throw ApiException(r.statusCode, r.body);
    }
    final data = jsonDecode(r.body) as Map<String, dynamic>;
    return data['job_id'] as String;
  }

  // ───────────── Job state / logs ─────────────
  Future<VideoJob> getJob(String jobId) async {
    final r = await http.get(_u('/jobs/$jobId'));
    if (r.statusCode != 200) {
      throw ApiException(r.statusCode, r.body);
    }
    return VideoJob.fromJson(jsonDecode(utf8.decode(r.bodyBytes)));
  }

  Future<String> getLogs(String jobId) async {
    final r = await http.get(_u('/jobs/$jobId/logs'));
    if (r.statusCode != 200) {
      throw ApiException(r.statusCode, r.body);
    }
    return utf8.decode(r.bodyBytes);
  }

  Future<List<JobSummary>> listJobs({int limit = 50}) async {
    final r = await http.get(_u('/jobs?limit=$limit'));
    if (r.statusCode != 200) {
      throw ApiException(r.statusCode, r.body);
    }
    final list = jsonDecode(utf8.decode(r.bodyBytes)) as List;
    return list
        .cast<Map<String, dynamic>>()
        .map(JobSummary.fromJson)
        .toList();
  }

  /// URL para abrir/descargar el video final en el sistema.
  String downloadUrl(String jobId) => '$baseUrl/jobs/$jobId/download';
}
