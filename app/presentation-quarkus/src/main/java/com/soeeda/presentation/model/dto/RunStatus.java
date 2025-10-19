package com.soeeda.presentation.model.dto;

public record RunStatus(String runId, String phase, Boolean succeeded, Boolean failed, String startedAt,
                        String finishedAt, String logsTail) {}
