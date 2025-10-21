package com.soeeda.presentation.client;

import java.util.List;

import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;

import com.soeeda.presentation.model.dto.ModelInfo;
import com.soeeda.presentation.model.dto.PromoteRequest;
import com.soeeda.presentation.model.dto.PromoteResponse;
import com.soeeda.presentation.model.dto.RetrainRequest;
import com.soeeda.presentation.model.dto.RunResponse;
import com.soeeda.presentation.model.dto.RunStatus;
import com.soeeda.presentation.model.dto.StartEdaRequest;

import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@Path("/api")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
@RegisterRestClient(configKey = "integration-api")
public interface IntegrationClient {

  @POST
  @Path("/eda/start")
  RunResponse startEda(StartEdaRequest req);

  @GET
  @Path("/eda/{runId}")
  RunStatus edaStatus(@PathParam("runId") String runId);

  @GET
  @Path("/models")
  List<ModelInfo> models();

  @POST
  @Path("/promote")
  PromoteResponse promote(PromoteRequest req);

  @POST
  @Path("/train/retrain")
  RunResponse retrain(RetrainRequest req);
}
