package com.soeeda.integration.service;

import io.fabric8.kubernetes.client.Config;
import io.fabric8.kubernetes.client.ConfigBuilder;
import io.fabric8.kubernetes.client.KubernetesClient;
import io.fabric8.kubernetes.client.KubernetesClientBuilder;
import jakarta.annotation.PreDestroy;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class KubernetesClientProducer {

    @ConfigProperty(name = "k8s.namespace")
    String namespace;

    private KubernetesClient client;

    @Produces
    @ApplicationScoped
    public KubernetesClient produceClient() {
        if (client == null) {
            Config config = new ConfigBuilder().withNamespace(namespace).build();
            client = new KubernetesClientBuilder().withConfig(config).build();
        }
        return client;
    }

    @PreDestroy
    void close() {
        if (client != null) {
            client.close();
        }
    }
}
