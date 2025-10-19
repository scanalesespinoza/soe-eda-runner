package com.soeeda.integration.service;

import com.soeeda.integration.model.dto.RunStatus;
import com.soeeda.integration.util.JsonUtil;
import io.fabric8.kubernetes.api.model.Pod;
import io.fabric8.kubernetes.api.model.PodList;
import io.fabric8.kubernetes.api.model.batch.v1.Job;
import io.fabric8.kubernetes.api.model.batch.v1.JobBuilder;
import io.fabric8.kubernetes.api.model.batch.v1.JobStatus;
import io.fabric8.kubernetes.client.KubernetesClient;
import io.fabric8.kubernetes.client.KubernetesClientException;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@ApplicationScoped
public class K8sJobService {

    private static final Logger LOG = Logger.getLogger(K8sJobService.class);
    private static final String CONTAINER_NAME = "runner";

    @Inject
    KubernetesClient client;

    @ConfigProperty(name = "k8s.namespace")
    String namespace;

    @ConfigProperty(name = "k8s.job.image")
    String jobImage;

    public String startEda(String datasetPath, String outputPath, String outliersCol) {
        String runId = UUID.randomUUID().toString().substring(0, 8);
        String jobName = "eda-run-" + runId;
        Job job = baseJobBuilder(jobName)
            .editOrNewSpec()
                .withTtlSecondsAfterFinished(1800)
                .editOrNewTemplate()
                    .editOrNewSpec()
                        .withRestartPolicy("Never")
                        .addNewContainer()
                            .withName(CONTAINER_NAME)
                            .withImage(jobImage)
                            .withArgs("python", "/app/eda.py",
                                "--input", datasetPath,
                                "--output", outputPath + "/" + runId,
                                "--outliers-col", outliersCol)
                        .endContainer()
                    .endSpec()
                .endTemplate()
            .endSpec()
            .build();

        client.batch().v1().jobs().inNamespace(namespace).resource(job).create();
        LOG.infov("EDA job {0} created", jobName);
        return runId;
    }

    public String startTrain(String datasetPath, Map<String, Object> params) {
        String runId = UUID.randomUUID().toString().substring(0, 8);
        String jobName = "train-run-" + runId;
        String paramsJson = JsonUtil.toJson(params);
        Job job = baseJobBuilder(jobName)
            .editOrNewSpec()
                .withTtlSecondsAfterFinished(1800)
                .editOrNewTemplate()
                    .editOrNewSpec()
                        .withRestartPolicy("Never")
                        .addNewContainer()
                            .withName(CONTAINER_NAME)
                            .withImage(jobImage)
                            .withArgs("python", "/app/train.py",
                                "--dataset", datasetPath,
                                "--params", paramsJson)
                        .endContainer()
                    .endSpec()
                .endTemplate()
            .endSpec()
            .build();

        client.batch().v1().jobs().inNamespace(namespace).resource(job).create();
        LOG.infov("Training job {0} created", jobName);
        return runId;
    }

    public RunStatus status(String runId) {
        String jobName = guessJobName(runId);
        try {
            Job job = client.batch().v1().jobs().inNamespace(namespace).withName(jobName).get();
            if (job == null) {
                return new RunStatus(runId, "NOT_FOUND", 0, 0, null, null, null);
            }
            JobStatus status = job.getStatus();
            String phase = derivePhase(status);
            Instant startedAt = Optional.ofNullable(status.getStartTime()).map(Instant::parse).orElse(null);
            Instant completedAt = Optional.ofNullable(status.getCompletionTime()).map(Instant::parse).orElse(null);
            Integer succeeded = Optional.ofNullable(status.getSucceeded()).orElse(0);
            Integer failed = Optional.ofNullable(status.getFailed()).orElse(0);
            String logs = tailLogs(jobName);
            return new RunStatus(runId, phase, succeeded, failed, startedAt, completedAt, logs);
        } catch (KubernetesClientException e) {
            LOG.errorf(e, "Unable to fetch job status for %s", jobName);
            return new RunStatus(runId, "ERROR", 0, 0, null, null, e.getMessage());
        }
    }

    private JobBuilder baseJobBuilder(String jobName) {
        return new JobBuilder()
            .withNewMetadata()
                .withName(jobName)
                .addToLabels("app", "integration")
                .addToLabels("app.kubernetes.io/managed-by", "integration-api")
            .endMetadata();
    }

    private String guessJobName(String runId) {
        if (runId.startsWith("train-run-")) {
            return runId;
        }
        if (runId.startsWith("eda-run-")) {
            return runId;
        }
        return "eda-run-" + runId;
    }

    private String derivePhase(JobStatus status) {
        if (status == null) {
            return "UNKNOWN";
        }
        if (status.getFailed() != null && status.getFailed() > 0) {
            return "FAILED";
        }
        if (status.getSucceeded() != null && status.getSucceeded() > 0) {
            return "SUCCEEDED";
        }
        if (status.getActive() != null && status.getActive() > 0) {
            return "RUNNING";
        }
        return Optional.ofNullable(status.getConditions())
            .map(List::stream)
            .flatMap(stream -> stream.filter(c -> "True".equalsIgnoreCase(c.getStatus())).findFirst())
            .map(condition -> condition.getType().toUpperCase())
            .orElse("PENDING");
    }

    private String tailLogs(String jobName) {
        try {
            PodList pods = client.pods().inNamespace(namespace)
                .withLabel("job-name", jobName)
                .list();
            if (pods == null || pods.getItems().isEmpty()) {
                return null;
            }
            Pod pod = pods.getItems().get(0);
            return client.pods().inNamespace(namespace)
                .withName(pod.getMetadata().getName())
                .inContainer(CONTAINER_NAME)
                .tailingLines(100)
                .getLog();
        } catch (KubernetesClientException e) {
            LOG.warnf(e, "Unable to fetch logs for job %s", jobName);
            return e.getMessage();
        }
    }
}
