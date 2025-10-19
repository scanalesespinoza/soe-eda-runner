package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record RunStatus(
    @JsonProperty("runId") String runId,
    @JsonProperty("phase") String phase,
    @JsonProperty("succeeded") Integer succeeded,
    @JsonProperty("failed") Integer failed,
    @JsonProperty("startedAt") Instant startedAt,
    @JsonProperty("finishedAt") Instant finishedAt,
    @JsonProperty("logsTail") String logsTail
) {
}
