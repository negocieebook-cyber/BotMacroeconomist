const { existsSync } = require("fs");
const { join } = require("path");
const { spawnSync } = require("child_process");

const projectRoot = join(__dirname, "..");
const commandArgs = process.argv.slice(2);
const requirementsFile = join(projectRoot, "requirements.txt");

/**
 * Wraps a path in double-quotes so that Windows shell handles spaces correctly.
 */
function q(p) {
  return `"${p}"`;
}

const pythonCandidates = [
  {
    command: join(projectRoot, ".venv", "Scripts", "python.exe"),
    prefixArgs: [],
    label: ".venv",
  },
  {
    command: "python",
    prefixArgs: [],
    label: "python",
  },
  {
    command: "py",
    prefixArgs: ["-3"],
    label: "py -3",
  },
];

function runProcess(command, args, options = {}) {
  const isWin = process.platform === "win32";

  if (isWin) {
    // On Windows, build the full command line ourselves so that paths with
    // spaces are properly quoted, then run through cmd.exe.
    const parts = [q(command), ...args.map((a) => q(a))];
    return spawnSync(parts.join(" "), {
      cwd: projectRoot,
      stdio: options.stdio || "pipe",
      shell: true,
    });
  }

  return spawnSync(command, args, {
    cwd: projectRoot,
    stdio: options.stdio || "pipe",
    shell: false,
  });
}

function canUseCandidate(candidate) {
  if (candidate.command.endsWith(".exe") && !existsSync(candidate.command)) {
    return false;
  }

  const check = runProcess(candidate.command, [
    ...candidate.prefixArgs,
    "--version",
  ]);
  return !check.error && check.status === 0;
}

function resolvePython() {
  for (const candidate of pythonCandidates) {
    if (canUseCandidate(candidate)) {
      console.log(`Usando Python: ${candidate.label} (${candidate.command})`);
      return candidate;
    }
  }

  return null;
}

function pythonArgs(candidate, extraArgs) {
  return [...candidate.prefixArgs, ...extraArgs];
}

function ensureDependencies(candidate) {
  const importCheck = runProcess(
    candidate.command,
    pythonArgs(candidate, ["-c", "import chromadb"])
  );

  if (importCheck.status === 0) {
    console.log("Dependencias Python OK.");
    return 0;
  }

  console.log(
    `Dependencias Python ausentes em ${candidate.label}. Instalando requirements.txt...`
  );

  const install = runProcess(
    candidate.command,
    pythonArgs(candidate, ["-m", "pip", "install", "-r", requirementsFile]),
    { stdio: "inherit" }
  );

  if (install.error && install.error.code === "ENOENT") {
    return 1;
  }

  return install.status === null ? 1 : install.status;
}

function startBot(candidate) {
  const mainPy = join(projectRoot, "main.py");
  const result = runProcess(
    candidate.command,
    pythonArgs(candidate, [mainPy, ...commandArgs]),
    { stdio: "inherit" }
  );

  return result.status === null ? 1 : result.status;
}

// ── Main ──────────────────────────────────────────────────────────────
const python = resolvePython();

if (!python) {
  console.error(
    "Nao encontrei um executavel Python. Ative a .venv ou instale Python antes de usar npm run dev."
  );
  process.exit(1);
}

const dependenciesExitCode = ensureDependencies(python);
if (dependenciesExitCode !== 0) {
  console.error(
    "Nao foi possivel preparar as dependencias Python automaticamente."
  );
  process.exit(dependenciesExitCode);
}

process.exit(startBot(python));
