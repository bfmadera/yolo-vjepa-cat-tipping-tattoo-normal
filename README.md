## Cat Ear Sterilization Mark Detection

This project is part of an undergraduate Computer Engineering thesis at the University of São Paulo (USP), Brazil. It explores computer vision techniques to automatically detect visible sterilization-related ear markings in cats, including **ear-tipping and ear tattoos**, to support ethical community cat population management.

The project includes a curated dataset of 449 cat images with 932 annotated ear regions, a custom Python annotation interface, and a YOLO11s object detector trained to distinguish between two classes: **marked ear** and **normal ear**.

Additional experiments explore traditional image processing methods, V-JEPA 2 visual embeddings, and ONNX export for potential future deployment on embedded computer vision systems.

Developed in connection with the **Gatos do C2** university extension project at USP São Carlos.

**Note:** The system identifies visible ear markings; it does not clinically determine whether a cat has been sterilized.
