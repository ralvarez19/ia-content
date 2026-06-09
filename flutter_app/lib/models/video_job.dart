import 'dart:io';

/// Modelos del cliente: estructuras que reflejan lo que devuelve el backend.

enum JobStatus { queued, running, completed, failed }

JobStatus _statusFromString(String? s) {
  switch (s) {
    case 'queued':    return JobStatus.queued;
    case 'running':   return JobStatus.running;
    case 'completed': return JobStatus.completed;
    case 'failed':    return JobStatus.failed;
  }
  return JobStatus.queued;
}

/// Una escena del lado cliente: se llena desde el formulario y se mandan
/// todas como JSON al backend en POST /jobs.
class SceneInput {
  int sceneNumber;
  String description;
  String dialogue;
  File? referenceImage;

  SceneInput({
    required this.sceneNumber,
    this.description = '',
    this.dialogue = '',
    this.referenceImage,
  });

  Map<String, dynamic> toJsonMetadata() => {
        'scene_number': sceneNumber,
        'scene_description': description.trim(),
        'dialogue': dialogue.trim(),
      };
}

/// Escena tal como llega del backend (incluye has_reference_image).
class Scene {
  final int sceneNumber;
  final String sceneDescription;
  final String dialogue;
  final bool hasReferenceImage;

  const Scene({
    required this.sceneNumber,
    required this.sceneDescription,
    required this.dialogue,
    required this.hasReferenceImage,
  });

  factory Scene.fromJson(Map<String, dynamic> j) => Scene(
        sceneNumber: j['scene_number'] ?? 0,
        sceneDescription: j['scene_description'] ?? '',
        dialogue: j['dialogue'] ?? '',
        hasReferenceImage: j['has_reference_image'] ?? false,
      );
}

class VideoJob {
  final String jobId;
  final String title;
  final List<Scene> scenes;
  final int durationSeconds;
  final String aspectRatio;
  final bool generateVoice;
  final bool generateVideo;
  final String? voiceId;
  final String? style;
  final bool musicEnabled;

  final JobStatus status;
  final int progress;
  final String currentStep;
  final String createdAt;
  final String updatedAt;
  final String? error;
  final String? outputVideo;

  const VideoJob({
    required this.jobId,
    required this.title,
    required this.scenes,
    required this.durationSeconds,
    required this.aspectRatio,
    required this.generateVoice,
    required this.generateVideo,
    this.voiceId,
    this.style,
    required this.musicEnabled,
    required this.status,
    required this.progress,
    required this.currentStep,
    required this.createdAt,
    required this.updatedAt,
    this.error,
    this.outputVideo,
  });

  factory VideoJob.fromJson(Map<String, dynamic> j) {
    final scenesRaw = (j['scenes'] as List?) ?? const [];
    return VideoJob(
      jobId: j['job_id'] ?? '',
      title: j['title'] ?? '',
      scenes: scenesRaw
          .cast<Map<String, dynamic>>()
          .map(Scene.fromJson)
          .toList(),
      durationSeconds: j['duration_seconds'] ?? 0,
      aspectRatio: j['aspect_ratio'] ?? '9:16',
      generateVoice: j['generate_voice'] ?? false,
      generateVideo: j['generate_video'] ?? false,
      voiceId: j['voice_id'],
      style: j['style'],
      musicEnabled: j['music_enabled'] ?? false,
      status: _statusFromString(j['status']),
      progress: j['progress'] ?? 0,
      currentStep: j['current_step'] ?? '',
      createdAt: j['created_at'] ?? '',
      updatedAt: j['updated_at'] ?? '',
      error: j['error'],
      outputVideo: j['output_video'],
    );
  }
}

class JobSummary {
  final String jobId;
  final String title;
  final JobStatus status;
  final int progress;
  final int scenesCount;
  final String createdAt;
  final String? outputVideo;

  const JobSummary({
    required this.jobId,
    required this.title,
    required this.status,
    required this.progress,
    required this.scenesCount,
    required this.createdAt,
    this.outputVideo,
  });

  factory JobSummary.fromJson(Map<String, dynamic> j) => JobSummary(
        jobId: j['job_id'] ?? '',
        title: j['title'] ?? '',
        status: _statusFromString(j['status']),
        progress: j['progress'] ?? 0,
        scenesCount: j['scenes_count'] ?? 0,
        createdAt: j['created_at'] ?? '',
        outputVideo: j['output_video'],
      );
}
