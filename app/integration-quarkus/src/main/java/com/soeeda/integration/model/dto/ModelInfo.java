package com.soeeda.integration.model.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.Map;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record ModelInfo(
    @JsonProperty("modelUri") String modelUri,
    @JsonProperty("createdAt") Instant createdAt,
    @JsonProperty("metrics") Map<String, Object> metrics,
    @JsonProperty("tags") Map<String, String> tags
) {
}
