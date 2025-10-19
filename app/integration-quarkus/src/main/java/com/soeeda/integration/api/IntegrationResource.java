package com.soeeda.integration.api;

import com.soeeda.integration.model.dto.ModelInfo;
import com.soeeda.integration.model.dto.PromoteRequest;
import com.soeeda.integration.model.dto.PromoteResponse;
import com.soeeda.integration.model.dto.RunResponse;
import com.soeeda.integration.model.dto.RunStatus;
import com.soeeda.integration.model.dto.StartEdaRequest;
import com.soeeda.integration.model.dto.StartTrainRequest;
import com.soeeda.integration.service.GitOpsService;
import com.soeeda.integration.service.K8sJobService;
import com.soeeda.integration.service.ModelRegistryService;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@Path("/api")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class IntegrationResource {

    @Inject
    K8sJobService k8sJobService;

    @Inject
    ModelRegistryService modelRegistryService;

    @Inject
    GitOpsService gitOpsService;

    @POST
    @Path("/eda/start")
    public RunResponse startEda(StartEdaRequest request) {
        String outputPath = Optional.ofNullable(request.outputPath()).orElse("/out");
        String runId = k8sJobService.startEda(
            request.datasetPath(),
            outputPath,
            Optional.ofNullable(request.outliersCol()).orElse("charges"));
        return new RunResponse(runId, "SUBMITTED", "EDA job submitted");
    }

    @GET
    @Path("/eda/{runId}")
    public RunStatus edaStatus(@PathParam("runId") String runId) {
        return k8sJobService.status(runId);
    }

    @POST
    @Path("/train/start")
    public RunResponse startTrain(StartTrainRequest request) {
        Map<String, Object> params = Optional.ofNullable(request.params()).orElse(Map.of());
        String runId = k8sJobService.startTrain(request.datasetPath(), params);
        return new RunResponse(runId, "SUBMITTED", "Training job submitted");
    }

    @GET
    @Path("/models")
    public List<ModelInfo> models() {
        return modelRegistryService.listModels();
    }

    @POST
    @Path("/promote")
    public PromoteResponse promote(PromoteRequest request) {
        return gitOpsService.promote(request.modelUri());
    }
}
