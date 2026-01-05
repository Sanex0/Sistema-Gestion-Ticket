# Directorio de Uploads

Este directorio almacena todos los archivos adjuntos subidos por usuarios y operadores.

## Estructura

Los archivos se organizan por ticket:

```
uploads/
├── ticket_1/
│   ├── 20251229_103045_abc123.pdf
│   └── 20251229_104512_def456.jpg
├── ticket_2/
│   └── 20251229_110230_ghi789.docx
└── ...
```

## Importante

- No versionar archivos subidos en Git
- Hacer backup regular de este directorio
- Verificar permisos de escritura
- Implementar limpieza de archivos huérfanos
