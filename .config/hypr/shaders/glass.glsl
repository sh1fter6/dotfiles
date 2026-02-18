precision mediump float;
varying vec2 v_texcoord;
uniform sampler2D tex;

void main() {
    vec4 color = texture2D(tex, v_texcoord);

    // Calculamos el valor máximo de los componentes RGB para detectar negro
    float max_color = max(max(color.r, color.g), color.b);
    
    // Si el color es un negro o gris muy oscuro (típico de fondos dark mode)
    if (max_color < 0.2) {
        // Reducimos el alpha proporcionalmente, pero manteniendo un suelo de 0.3
        // para que las letras oscuras o sombras no desaparezcan del todo.
        color.a = max_color * 3.0 + 0.3;
    } else {
        // Para cualquier otro color (imágenes, texto blanco, botones), 100% opaco
        color.a = 1.0;
    }

    gl_FragColor = color;
}
