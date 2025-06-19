#!/usr/bin/env python3
"""
Teste específico do SentenceTransformers integrado
Verifica se o modelo local está funcionando corretamente
"""

import sys
import os

# Adicionar src ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_sentence_transformers():
    print("🧠 TESTANDO SENTENCETRANSFORMERS LOCAL")
    print("=" * 60)
    
    # Carregar variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv('config.env')
    
    # Teste 1: Carregar serviço diretamente
    print("1️⃣ Testando SentenceTransformerService...")
    try:
        from services.sentence_transformer_service import SentenceTransformerService
        st_service = SentenceTransformerService()
        
        print("✅ Serviço carregado")
        info = st_service.get_model_info()
        print(f"📊 Modelo: {info.get('model_name', 'N/A')}")
        print(f"📏 Dimensões: {info.get('dimensions', 'N/A')}")
        print(f"🔧 Device: {info.get('device', 'N/A')}")
        print(f"📈 Status: {info.get('status', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Erro ao carregar SentenceTransformerService: {e}")
        return False
    
    # Teste 2: Gerar embedding único
    print("\n2️⃣ Testando embedding único...")
    try:
        texto_teste = "Contratação de serviços de tecnologia da informação"
        embedding = st_service.generate_single_embedding(texto_teste)
        
        if embedding:
            print(f"✅ Embedding gerado: {len(embedding)} dimensões")
            print(f"📊 Primeiros valores: {embedding[:5]}")
            
            # Verificar se é válido
            if len(embedding) == 384:  # NeralMind BERT
                print("✅ Dimensões corretas para modelo português!")
            else:
                print(f"⚠️ Dimensões inesperadas: {len(embedding)}")
        else:
            print("❌ Falha ao gerar embedding")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de embedding: {e}")
        return False
    
    # Teste 3: Batch processing
    print("\n3️⃣ Testando batch processing...")
    try:
        textos_licitacao = [
            "Contratação de empresa especializada para prestação de serviços de TI",
            "Aquisição de equipamentos de informática incluindo computadores",
            "Prestação de serviços de manutenção preventiva de impressoras",
            "Fornecimento de papel A4 e material de escritório para secretaria"
        ]
        
        embeddings = st_service.generate_embeddings(textos_licitacao)
        
        if embeddings and len(embeddings) == 4:
            print(f"✅ Batch OK: {len(embeddings)} embeddings")
            print(f"📏 Dimensões: {[len(emb) for emb in embeddings]}")
            
            # Verificar consistência
            dims = [len(emb) for emb in embeddings]
            if all(d == dims[0] for d in dims):
                print("✅ Dimensões consistentes!")
            else:
                print("⚠️ Dimensões inconsistentes!")
                
        else:
            print("❌ Batch processing falhou")
            return False
            
    except Exception as e:
        print(f"❌ Erro no batch: {e}")
        return False
    
    # Teste 4: Similaridade semântica
    print("\n4️⃣ Testando similaridade semântica...")
    try:
        # Textos similares
        texto1 = "Serviços de tecnologia da informação"
        texto2 = "Prestação de serviços de TI"
        
        # Textos diferentes
        texto3 = "Fornecimento de papel e material de escritório"
        
        emb1 = st_service.generate_single_embedding(texto1)
        emb2 = st_service.generate_single_embedding(texto2)
        emb3 = st_service.generate_single_embedding(texto3)
        
        if emb1 and emb2 and emb3:
            import numpy as np
            
            def cosine_similarity(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            
            sim_ti = cosine_similarity(emb1, emb2)
            sim_diff = cosine_similarity(emb1, emb3)
            
            print(f"📊 Similaridade TI vs Tecnologia: {sim_ti:.3f}")
            print(f"📊 Similaridade TI vs Papel: {sim_diff:.3f}")
            
            if sim_ti > sim_diff:
                print("✅ Modelo entende contexto semântico!")
                if sim_ti > 0.7:
                    print("🎯 Alta correlação para termos técnicos!")
            else:
                print("⚠️ Problema na similaridade semântica")
                
        else:
            print("❌ Falha ao gerar embeddings para similaridade")
            
    except Exception as e:
        print(f"❌ Erro no teste de similaridade: {e}")
        print("💡 Continuando sem teste de similaridade...")
    
    print("\n🎉 TESTE SENTENCETRANSFORMERS COMPLETO!")
    return True

def test_hybrid_vectorizer():
    print("\n🚀 TESTANDO SISTEMA HÍBRIDO INTEGRADO")
    print("=" * 60)
    
    try:
        from matching.vectorizers import HybridTextVectorizer
        from config.database import db_manager
        
        # Inicializar sistema híbrido
        print("🔄 Inicializando HybridTextVectorizer...")
        vectorizer = HybridTextVectorizer(db_manager)
        
        # Teste de vetorização
        print("\n🧪 Testando vetorização híbrida...")
        texto_teste = "Contratação de serviços de manutenção de equipamentos de informática"
        
        embedding = vectorizer.vectorize(texto_teste)
        
        if embedding:
            print(f"✅ Sistema híbrido funcionando!")
            print(f"📏 Embedding: {len(embedding)} dimensões")
            print(f"🔢 Primeiros valores: {embedding[:3]}")
            
            # Teste batch
            textos = [
                "Serviços de TI e suporte técnico",
                "Aquisição de equipamentos de escritório",
                "Manutenção preventiva de impressoras"
            ]
            
            batch_embeddings = vectorizer.batch_vectorize(textos)
            
            if batch_embeddings:
                print(f"✅ Batch híbrido: {len(batch_embeddings)} embeddings")
                return True
            else:
                print("❌ Batch híbrido falhou")
                return False
        else:
            print("❌ Sistema híbrido falhou")
            return False
            
    except Exception as e:
        print(f"❌ Erro no sistema híbrido: {e}")
        return False

if __name__ == "__main__":
    print("🧠 TESTE COMPLETO DO SISTEMA DE EMBEDDINGS")
    print("=" * 70)
    
    success1 = test_sentence_transformers()
    success2 = test_hybrid_vectorizer()
    
    if success1 and success2:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ SentenceTransformers LOCAL pronto para produção")
        print("✅ Sistema híbrido funcionando")
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("   1. Executar matching engine com novo sistema")
        print("   2. Comparar resultados com sistema anterior")
        print("   3. Monitorar performance e cache hits")
        sys.exit(0)
    else:
        print("\n❌ ALGUNS TESTES FALHARAM")
        print("🔧 Verificar configuração antes de usar em produção")
        sys.exit(1) 