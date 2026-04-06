package com.xiyou.video.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;

@Component
public class JwtUtil {

    @Value("${app.jwt.secret}")
    private String secret;

    @Value("${app.jwt.expire-hours}")
    private Integer expireHours;

    private SecretKey secretKey;

    @PostConstruct
    public void init() {
        byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
        byte[] padded = new byte[Math.max(bytes.length, 32)];
        System.arraycopy(bytes, 0, padded, 0, bytes.length);
        this.secretKey = Keys.hmacShaKeyFor(padded);
    }

    public String generateToken(AuthUser user) {
        LocalDateTime expireTime = LocalDateTime.now().plusHours(expireHours);
        return Jwts.builder()
                .claim("userId", user.getId())
                .claim("username", user.getUsername())
                .claim("role", user.getRole())
                .setExpiration(Date.from(expireTime.atZone(ZoneId.systemDefault()).toInstant()))
                .signWith(secretKey, SignatureAlgorithm.HS256)
                .compact();
    }

    public AuthUser parseToken(String token) {
        Claims claims = Jwts.parserBuilder()
                .setSigningKey(secretKey)
                .build()
                .parseClaimsJws(token)
                .getBody();
        Long userId = ((Number) claims.get("userId")).longValue();
        String username = (String) claims.get("username");
        String role = (String) claims.get("role");
        return new AuthUser(userId, username, role);
    }
}
