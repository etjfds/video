package com.xiyou.video.config;

import com.xiyou.video.security.AuthInterceptor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Path;
import java.nio.file.Paths;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    private final AuthInterceptor authInterceptor;
    private final String imageDir;

    public WebMvcConfig(AuthInterceptor authInterceptor,
                        @Value("${app.file.image-dir}") String imageDir) {
        this.authInterceptor = authInterceptor;
        this.imageDir = imageDir;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authInterceptor).addPathPatterns("/**");
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins("*")
                .allowedHeaders("*")
                .allowedMethods("*");
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path imagePath = Paths.get(imageDir).toAbsolutePath().normalize();
        registry.addResourceHandler("/img/**")
                .addResourceLocations(
                        "file:" + imagePath.toString() + "/",
                        "classpath:/static/img/"
                );
    }
}
