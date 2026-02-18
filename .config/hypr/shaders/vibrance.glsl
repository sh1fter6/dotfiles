#version 300 es
precision highp float;

in vec2 v_texcoord;
out vec4 fragColor;
uniform sampler2D tex;

const float VIBRANCE = 0.5;    // Satura selectivamente colores apagados
const float SATURATION = 1.03;  // Compensación de gamut 60% sRGB
const float CONTRAST = 1.03;    // Mejora el ratio 800:1 sin perder detalle
const float GAMMA = 1.0;       // Profundidad en negros (evita el grisáceo del TN)

const vec3 LUMA_COEFF = vec3(0.2126, 0.7152, 0.0722);

void main() {
    vec4 color = texture(tex, v_texcoord);
    
    float luma = dot(color.rgb, LUMA_COEFF);
    
    float max_c = max(color.r, max(color.g, color.b));
    float min_c = min(color.r, min(color.g, color.b));
    float sat_mask = max_c - min_c;
    
    float vibrance_amount = VIBRANCE * (1.0 - sat_mask);
    color.rgb = mix(vec3(luma), color.rgb, 1.0 + vibrance_amount);
    
    color.rgb = mix(vec3(luma), color.rgb, SATURATION);

    color.rgb = clamp((color.rgb - 0.5) * CONTRAST + 0.5, 0.0, 1.0);
    color.rgb = pow(color.rgb, vec3(1.0 / GAMMA));

    fragColor = color;
}
