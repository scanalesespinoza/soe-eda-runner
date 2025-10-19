package com.soeeda.integration.service;

import com.soeeda.integration.model.dto.ModelInfo;
import com.soeeda.integration.util.JsonUtil;
import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.core.exception.SdkException;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectTaggingRequest;
import software.amazon.awssdk.services.s3.model.ListObjectsV2Request;
import software.amazon.awssdk.services.s3.model.ListObjectsV2Response;
import software.amazon.awssdk.services.s3.model.S3Object;
import software.amazon.awssdk.services.s3.model.Tag;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@ApplicationScoped
public class ModelRegistryService {

    private static final Logger LOG = Logger.getLogger(ModelRegistryService.class);

    @ConfigProperty(name = "s3.endpoint")
    String endpoint;

    @ConfigProperty(name = "s3.access-key")
    String accessKey;

    @ConfigProperty(name = "s3.secret-key")
    String secretKey;

    @ConfigProperty(name = "s3.bucket", defaultValue = "models")
    String bucket;

    private S3Client s3Client;

    @PostConstruct
    void init() {
        s3Client = S3Client.builder()
            .endpointOverride(URI.create(endpoint))
            .credentialsProvider(StaticCredentialsProvider.create(
                AwsBasicCredentials.create(accessKey, secretKey)))
            .forcePathStyle(true)
            .region(Region.US_EAST_1)
            .build();
    }

    public List<ModelInfo> listModels() {
        List<ModelInfo> models = new ArrayList<>();
        String continuationToken = null;
        do {
            ListObjectsV2Request.Builder request = ListObjectsV2Request.builder()
                .bucket(bucket)
                .delimiter("/");
            if (continuationToken != null) {
                request.continuationToken(continuationToken);
            }
            ListObjectsV2Response response = s3Client.listObjectsV2(request.build());
            continuationToken = response.nextContinuationToken();
            List<S3Object> contents = response.contents();
            if (contents == null) {
                continue;
            }
            for (S3Object object : contents) {
                if (!object.key().endsWith("metrics.json")) {
                    continue;
                }
                models.add(buildModelInfo(object));
            }
        } while (continuationToken != null);
        models.sort((left, right) -> {
            if (left.createdAt() == null || right.createdAt() == null) {
                return 0;
            }
            return right.createdAt().compareTo(left.createdAt());
        });
        return models;
    }

    private ModelInfo buildModelInfo(S3Object metricsObject) {
        String prefix = metricsObject.key().substring(0, metricsObject.key().lastIndexOf("/"));
        String modelUri = "s3://" + bucket + "/" + prefix;
        Map<String, Object> metrics = readMetrics(metricsObject.key());
        Map<String, String> tags = readTags(metricsObject.key());
        Instant createdAt = metricsObject.lastModified();
        return new ModelInfo(modelUri, createdAt, metrics, tags);
    }

    private Map<String, Object> readMetrics(String key) {
        try (ResponseInputStream<?> response = s3Client.getObject(GetObjectRequest.builder()
            .bucket(bucket)
            .key(key)
            .build());
             BufferedReader reader = new BufferedReader(new InputStreamReader(response, StandardCharsets.UTF_8))) {
            String body = reader.lines().collect(Collectors.joining());
            return JsonUtil.fromJson(body);
        } catch (SdkException | java.io.IOException e) {
            LOG.warnf(e, "Unable to read metrics from %s", key);
            return Collections.emptyMap();
        }
    }

    private Map<String, String> readTags(String key) {
        try {
            List<Tag> tagSet = s3Client.getObjectTagging(GetObjectTaggingRequest.builder()
                .bucket(bucket)
                .key(key)
                .build()).tagSet();
            Map<String, String> tags = new HashMap<>();
            for (Tag tag : tagSet) {
                tags.put(tag.key(), tag.value());
            }
            return tags;
        } catch (SdkException e) {
            LOG.debugf("No tags found for %s: %s", key, e.getMessage());
            return Collections.emptyMap();
        }
    }
}
