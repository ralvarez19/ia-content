import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config.dart';
import '../models/video_job.dart';
import '../services/api_service.dart';

class JobProgressScreen extends StatefulWidget {
  const JobProgressScreen({super.key, required this.jobId});
  final String jobId;

  @override
  State<JobProgressScreen> createState() => _JobProgressScreenState();
}

class _JobProgressScreenState extends State<JobProgressScreen> {
  final _api = ApiService();
  VideoJob? _job;
  String _logs = '';
  Timer? _timer;
  bool _loading = true;
  String? _error;

  final _logScroll = ScrollController();

  @override
  void initState() {
    super.initState();
    _fetch();
    _timer = Timer.periodic(
      Duration(seconds: AppConfig.progressPollSeconds),
      (_) => _fetch(),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _logScroll.dispose();
    super.dispose();
  }

  Future<void> _fetch() async {
    try {
      final job = await _api.getJob(widget.jobId);
      final logs = await _api.getLogs(widget.jobId);
      if (!mounted) return;
      setState(() {
        _job = job;
        _logs = logs;
        _loading = false;
        _error = null;
      });
      if (job.status == JobStatus.completed || job.status == JobStatus.failed) {
        _timer?.cancel();
      }
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_logScroll.hasClients) {
          _logScroll.jumpTo(_logScroll.position.maxScrollExtent);
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _openVideo() async {
    final url = Uri.parse(_api.downloadUrl(widget.jobId));
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No pude abrir el video con el reproductor')),
        );
      }
    }
  }

  Color _statusColor(JobStatus s) {
    switch (s) {
      case JobStatus.completed: return Colors.greenAccent;
      case JobStatus.failed:    return Colors.redAccent;
      case JobStatus.running:   return Colors.amberAccent;
      case JobStatus.queued:    return Colors.blueGrey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Job ${widget.jobId.substring(0, 8)}'),
        actions: [
          IconButton(
            tooltip: 'Refrescar',
            icon: const Icon(Icons.refresh),
            onPressed: _fetch,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text('Error: $_error'))
              : Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _statusCard(),
                      const SizedBox(height: 16),
                      Expanded(child: _logsCard()),
                      const SizedBox(height: 16),
                      Row(children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => Navigator.pop(context),
                            icon: const Icon(Icons.arrow_back),
                            label: const Text('Volver'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: (_job?.status == JobStatus.completed)
                                ? _openVideo : null,
                            icon: const Icon(Icons.play_circle_outline),
                            label: const Text('Abrir video final'),
                          ),
                        ),
                      ]),
                    ],
                  ),
                ),
    );
  }

  Widget _statusCard() {
    final job = _job!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(job.title.isEmpty ? '(sin título)' : job.title,
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Row(children: [
              Container(
                width: 12, height: 12,
                decoration: BoxDecoration(
                  color: _statusColor(job.status),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${job.status.name.toUpperCase()} · ${job.currentStep}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ]),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: job.progress / 100,
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
            ),
            const SizedBox(height: 6),
            Text('${job.progress}%',
                style: Theme.of(context).textTheme.bodySmall),
            if (job.error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.redAccent.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text('⚠ ${job.error}',
                    style: const TextStyle(color: Colors.redAccent)),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _logsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.terminal, size: 18),
              const SizedBox(width: 8),
              Text('Logs', style: Theme.of(context).textTheme.titleSmall),
            ]),
            const SizedBox(height: 8),
            Expanded(
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0B0B12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Scrollbar(
                  controller: _logScroll,
                  child: SingleChildScrollView(
                    controller: _logScroll,
                    child: SelectableText(
                      _logs.isEmpty ? '(sin logs aún)' : _logs,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 12,
                        height: 1.4,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
