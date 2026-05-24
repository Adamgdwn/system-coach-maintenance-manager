# System Capability Profile

The system capability profile is the public-install discovery layer. It assumes the first run may be on an unknown machine and uses bounded local checks to decide which agent surfaces, scan scopes, setup docs, and action paths are appropriate.

The profile detects:

- operating system, Linux distribution, and desktop/session family
- package managers and maintenance commands
- display stack and display-management commands
- privilege helpers such as `pkexec` or Windows elevation paths
- local model runtimes such as Ollama and available local model tags
- a small hardware summary including architecture and GPU visibility when read-only commands are available

The profile does not approve execution. It only helps the app decide what to show, what to disable, and which docs to recommend. Pop!_OS + COSMIC remains a first-class specialization when Pop/COSMIC signals are present; otherwise it degrades to advisory/hidden while Request Desk and deterministic triage remain available.

Machine-specific state belongs in local user paths such as the maintenance history directory or the user config path reported by the profile. It should not be committed to the repository.
