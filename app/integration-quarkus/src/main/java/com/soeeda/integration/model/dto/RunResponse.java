package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record RunResponse(
    @JsonProperty("runId") String runId,
    @JsonProperty("status") String status,
    @JsonProperty("message") String message
) {
}
