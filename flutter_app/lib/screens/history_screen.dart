import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/video_job.dart';
import '../services/api_service.dart';
import '../widgets/job_card.dart';
import 'job_progress_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final _api = ApiService();
  late Future<List<JobSummary>> _future;

  @override
  void initState() {
    super.initState();
    _future = _api.listJobs();
  }

  Future<void> _refresh() async {
    setState(() => _future = _api.listJobs());
    await _future;
  }

  Future<void> _open(JobSummary s) async {
    final url = Uri.parse(_api.downloadUrl(s.jobId));
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No pude abrir el video')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Historial'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _refresh),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<JobSummary>>(
          future: _future,
          builder: (ctx, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Center(child: Text('Error: ${snap.error}'));
            }
            final items = snap.data ?? [];
            if (items.isEmpty) {
              return const Center(
                child: Text('Aún no hay videos generados.'),
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) {
                final s = items[i];
                return JobCard(
                  summary: s,
                  onOpen: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => JobProgressScreen(jobId: s.jobId),
                    ),
                  ),
                  onDownload: () => _open(s),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
