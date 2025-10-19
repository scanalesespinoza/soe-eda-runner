package com.soeeda.presentation.model.dto;

import java.util.Map;

public record ModelInfo(String modelUri, String createdAt, Map<String, Object> metrics, Map<String, String> tags) {}
