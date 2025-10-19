package com.soeeda.integration.service;

import com.soeeda.integration.model.dto.PromoteResponse;
import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@ApplicationScoped
public class GitOpsService {

    private static final Logger LOG = Logger.getLogger(GitOpsService.class);

    @ConfigProperty(name = "gitops.repo.path")
    Path repoPath;

    @ConfigProperty(name = "gitops.overlay.path")
    String overlayPath;

    @ConfigProperty(name = "gitops.model.cm.name", defaultValue = "inference-cm")
    String configMapName;

    @ConfigProperty(name = "gitops.model.key", defaultValue = "MODEL_PATH")
    String modelKey;

    public PromoteResponse promote(String modelUri) {
        Path overlayDir = repoPath.resolve(overlayPath);
        Path configMapFile = overlayDir.resolve("configmaps.yaml");
        if (!Files.exists(configMapFile)) {
            return new PromoteResponse("ERROR", "ConfigMap manifest not found: " + configMapFile);
        }
        try {
            String original = Files.readString(configMapFile);
            String updated = updateModelPath(original, modelUri);
            if (original.equals(updated)) {
                LOG.infof("%s already set to %s", modelKey, modelUri);
                return new PromoteResponse("NOOP", modelKey + " already set");
            }
            Files.writeString(configMapFile, updated, StandardCharsets.UTF_8);
            String commitMessage = commitChanges(overlayDir, configMapFile, modelUri);
            return new PromoteResponse("UPDATED", commitMessage);
        } catch (IOException | InterruptedException e) {
            LOG.error("Unable to promote model", e);
            return new PromoteResponse("ERROR", e.getMessage());
        }
    }

    private String updateModelPath(String content, String modelUri) {
        String regex = "(" + Pattern.quote(modelKey) + ":\\s*)(\"?.*?\"?)";
        Pattern pattern = Pattern.compile(regex);
        Matcher matcher = pattern.matcher(content);
        if (matcher.find()) {
            return matcher.replaceFirst("$1\"" + modelUri + "\"");
        }
        String patch = String.format("  - name: %s\n    data:\n      %s: \"%s\"\n", configMapName, modelKey, modelUri);
        return content + System.lineSeparator() + patch;
    }

    private String commitChanges(Path workDir, Path file, String modelUri) throws IOException, InterruptedException {
        runGit(workDir, List.of("git", "add", repoPath.relativize(file).toString()));
        if (isTreeClean(workDir)) {
            return "No changes";
        }
        String message = String.format("chore: promote model %s", modelUri);
        runGit(workDir, List.of("git", "config", "user.name", "integration-bot"));
        runGit(workDir, List.of("git", "config", "user.email", "integration@example.com"));
        runGit(workDir, List.of("git", "commit", "-m", message));
        String commitId = runGit(workDir, List.of("git", "rev-parse", "HEAD"));
        return String.format("commit %s", commitId.strip());
    }

    private boolean isTreeClean(Path workDir) throws IOException, InterruptedException {
        String status = runGit(workDir, List.of("git", "status", "--porcelain"));
        return status.isBlank();
    }

    private String runGit(Path workDir, List<String> command) throws IOException, InterruptedException {
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.directory(workDir.toFile());
        Process process = builder.start();
        int exit = process.waitFor();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        String error = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);
        if (exit != 0) {
            throw new IOException("Git command failed: " + String.join(" ", command) + " -> " + error);
        }
        if (!error.isBlank()) {
            LOG.debugf("git stderr: %s", error);
        }
        return output;
    }
}
