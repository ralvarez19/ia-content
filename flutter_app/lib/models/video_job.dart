/// Modelos del cliente. Representan respuesta del backend FastAPI.
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

class VideoJob {
  final String jobId;
  final String title;
  final String scene;
  final String dialogue;
  final int clipsCount;
  final int durationSeconds;
  final String aspectRatio;
  final bool generateVoice;
  final bool generateVideo;
  final bool useReferenceImage;
  final bool hasReferenceImage;
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
    required this.scene,
    required this.dialogue,
    required this.clipsCount,
    required this.durationSeconds,
    required this.aspectRatio,
    required this.generateVoice,
    required this.generateVideo,
    required this.useReferenceImage,
    required this.hasReferenceImage,
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

  factory VideoJob.fromJson(Map<String, dynamic> j) => VideoJob(
        jobId: j['job_id'] ?? '',
        title: j['title'] ?? '',
        scene: j['scene'] ?? '',
        dialogue: j['dialogue'] ?? '',
        clipsCount: j['clips_count'] ?? 0,
        durationSeconds: j['duration_seconds'] ?? 0,
        aspectRatio: j['aspect_ratio'] ?? '9:16',
        generateVoice: j['generate_voice'] ?? false,
        generateVideo: j['generate_video'] ?? false,
        useReferenceImage: j['use_reference_image'] ?? false,
        hasReferenceImage: j['has_reference_image'] ?? false,
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

/// Versión liviana usada en el listado /jobs
class JobSummary {
  final String jobId;
  final String title;
  final JobStatus status;
  final int progress;
  final String createdAt;
  final String? outputVideo;

  const JobSummary({
    required this.jobId,
    required this.title,
    required this.status,
    required this.progress,
    required this.createdAt,
    this.outputVideo,
  });

  factory JobSummary.fromJson(Map<String, dynamic> j) => JobSummary(
        jobId: j['job_id'] ?? '',
        title: j['title'] ?? '',
        status: _statusFromString(j['status']),
        progress: j['progress'] ?? 0,
        createdAt: j['created_at'] ?? '',
        outputVideo: j['output_video'],
      );
}
