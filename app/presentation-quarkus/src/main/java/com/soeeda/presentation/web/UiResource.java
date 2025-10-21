package com.soeeda.presentation.web;

import java.util.List;
import java.util.Map;

import com.soeeda.presentation.client.IntegrationClient;
import com.soeeda.presentation.model.dto.ModelInfo;
import com.soeeda.presentation.model.dto.PromoteRequest;
import com.soeeda.presentation.model.dto.PromoteResponse;
import com.soeeda.presentation.model.dto.RetrainRequest;
import com.soeeda.presentation.model.dto.RunResponse;
import com.soeeda.presentation.model.dto.RunStatus;
import com.soeeda.presentation.model.dto.StartEdaRequest;

import io.quarkus.qute.Template;
import io.quarkus.qute.TemplateInstance;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.FormParam;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import org.eclipse.microprofile.rest.client.inject.RestClient;

@Path("/")
@Produces(MediaType.TEXT_HTML)
public class UiResource {

  @Inject
  Template index;

  @Inject
  Template eda;

  @Inject
  Template runs;

  @Inject
  Template models;

  @Inject
  Template report;

  @RestClient
  IntegrationClient client;

  @GET
  public TemplateInstance home() {
    return index.data("title", "SOE-EDA Runner UI");
  }

  @GET
  @Path("/eda")
  public TemplateInstance edaPage() {
    return eda.data("title", "Run EDA");
  }

  @POST
  @Path("/eda/start")
  @Consumes(MediaType.APPLICATION_FORM_URLENCODED)
  public TemplateInstance startEda(@FormParam("datasetPath") String datasetPath) {
    RunResponse resp = client.startEda(new StartEdaRequest(datasetPath, "/out", "charges"));
    return runs.data("title", "Runs")
               .data("message", "EDA submitted")
               .data("runId", resp.runId());
  }

  @GET
  @Path("/runs/{runId}")
  public TemplateInstance runStatus(@PathParam("runId") String runId) {
    RunStatus status = client.edaStatus(runId);
    return runs.data("title", "Run Status")
               .data("runId", runId)
               .data("status", status);
  }

  @GET
  @Path("/models")
  public TemplateInstance modelsPage() {
    List<ModelInfo> list = client.models();
    return models.data("title", "Models")
                 .data("models", list);
  }

  @POST
  @Path("/models/promote")
  @Consumes(MediaType.APPLICATION_FORM_URLENCODED)
  public TemplateInstance promote(@FormParam("modelUri") String modelUri) {
    PromoteResponse response = client.promote(new PromoteRequest(modelUri));
    List<ModelInfo> list = client.models();
    return models.data("title", "Models")
                 .data("models", list)
                 .data("promoted", Map.of(
                     "modelUri", modelUri,
                     "status", response.status(),
                     "commit", response.commitId()));
  }

  @GET
  @Path("/report/{runId}")
  public TemplateInstance reportPage(@PathParam("runId") String runId) {
    String reportUrl = "/out/" + runId + "/eda-report.html";
    return report.data("title", "EDA Report")
                 .data("reportUrl", reportUrl);
  }

  @POST
  @Path("/retrain")
  @Consumes(MediaType.APPLICATION_FORM_URLENCODED)
  public TemplateInstance retrain(@FormParam("datasetPath") String datasetPath) {
    RetrainRequest request = new RetrainRequest(datasetPath, "/out", Map.of());
    RunResponse response = client.retrain(request);
    return runs.data("title", "Runs")
               .data("message", "Retrain submitted")
               .data("runId", response.runId());
  }
}
