"""
Service para envio de emails
Verificação de conta, reset de senha e notificações
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os

logger = logging.getLogger(__name__)

class EmailService:
    """Service para gerenciar envio de emails"""
    
    def __init__(self):
        """Inicializar service com configurações de SMTP"""
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('FROM_NAME', 'Alicit')
        
        # URL base do frontend
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        # Verificar se configurações estão disponíveis
        self.is_configured = bool(self.smtp_user and self.smtp_password)
        
        if not self.is_configured:
            logger.warning("SMTP não configurado. Emails serão simulados no log.")
    
    def send_verification_email(self, email: str, name: str, token: str) -> bool:
        """
        Enviar email de verificação de conta
        
        Args:
            email: Email do destinatário
            name: Nome do usuário
            token: Token de verificação
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            subject = f"Verifique sua conta - {self.from_name}"
            verification_url = f"{self.frontend_url}/verify-email?token={token}"
            
            # Template HTML do email
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{self.from_name}</h1>
                    </div>
                    <div class="content">
                        <h2>Olá, {name}!</h2>
                        <p>Bem-vindo ao {self.from_name}! Para começar a usar nossa plataforma, você precisa verificar seu email.</p>
                        <p>Clique no botão abaixo para verificar sua conta:</p>
                        <p style="text-align: center;">
                            <a href="{verification_url}" class="button">Verificar Email</a>
                        </p>
                        <p>Ou copie e cole este link no seu navegador:</p>
                        <p><a href="{verification_url}">{verification_url}</a></p>
                        <p><strong>Este link expira em 24 horas.</strong></p>
                        <p>Se você não criou uma conta conosco, pode ignorar este email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 {self.from_name}. Todos os direitos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Texto simples como fallback
            text_body = f"""
            Olá, {name}!
            
            Bem-vindo ao {self.from_name}! Para começar a usar nossa plataforma, você precisa verificar seu email.
            
            Clique no link abaixo para verificar sua conta:
            {verification_url}
            
            Este link expira em 24 horas.
            
            Se você não criou uma conta conosco, pode ignorar este email.
            
            © 2024 {self.from_name}. Todos os direitos reservados.
            """
            
            return self._send_email(email, subject, text_body, html_body)
            
        except Exception as e:
            logger.error(f"Erro ao enviar email de verificação: {e}")
            return False
    
    def send_password_reset_code_email(self, email: str, name: str, code: str) -> bool:
        """
        Enviar email com código para reset de senha
        
        Args:
            email: Email do destinatário
            name: Nome do usuário
            code: Código de 6 dígitos para reset
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            subject = f"Código para Redefinir sua Senha - {self.from_name}"
            
            # Template HTML do email
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                    .header {{ background: #f8f9fa; padding: 20px; text-align: center; border-bottom: 1px solid #ddd; }}
                    .content {{ padding: 30px; }}
                    .code-box {{ font-size: 36px; font-weight: bold; text-align: center; background: #eee; padding: 20px; border-radius: 5px; letter-spacing: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; padding: 20px; border-top: 1px solid #ddd; }}
                    .warning {{ color: #dc3545; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>{self.from_name} - Redefinição de Senha</h2>
                    </div>
                    <div class="content">
                        <h3>Olá, {name}!</h3>
                        <p>Recebemos uma solicitação para redefinir a senha da sua conta.</p>
                        <p>Use o código abaixo para redefinir sua senha. Este código é válido por <strong>10 minutos</strong>.</p>
                        <div class="code-box">
                            {code}
                        </div>
                        <p>Se você não solicitou esta alteração, pode ignorar este email com segurança. Nenhuma alteração foi feita em sua conta.</p>
                        <p class="warning">Nunca compartilhe este código com ninguém.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 {self.from_name}. Todos os direitos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Texto simples como fallback
            text_body = f"""
            Olá, {name}!

            Use este código para redefinir sua senha no {self.from_name}:
            {code}

            Este código expira em 10 minutos.

            Se você não solicitou esta alteração, ignore este email.

            © 2024 {self.from_name}. Todos os direitos reservados.
            """
            
            return self._send_email(email, subject, text_body, html_body)
            
        except Exception as e:
            logger.error(f"Erro ao enviar email de código de reset de senha: {e}")
            return False
    
    def send_welcome_email(self, email: str, name: str) -> bool:
        """
        Enviar email de boas-vindas após verificação
        
        Args:
            email: Email do destinatário
            name: Nome do usuário
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            subject = f"Bem-vindo ao {self.from_name}!"
            dashboard_url = f"{self.frontend_url}/dashboard"
            
            # Template HTML do email
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #28a745; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .button {{ display: inline-block; background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; padding: 20px; }}
                    .feature {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #28a745; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Bem-vindo ao {self.from_name}!</h1>
                    </div>
                    <div class="content">
                        <h2>Olá, {name}!</h2>
                        <p>Sua conta foi verificada com sucesso! Agora você tem acesso completo à nossa plataforma.</p>
                        
                        <h3>🎁 Seu Trial Gratuito de 7 dias começou!</h3>
                        <p>Durante este período, você pode:</p>
                        
                        <div class="feature">
                            <strong>🏢 Cadastrar suas empresas</strong><br>
                            Registre até 3 empresas para participar dos matches
                        </div>
                        
                        <div class="feature">
                            <strong>🔍 Matches automáticos</strong><br>
                            Receba até 100 matches mensais com licitações relevantes
                        </div>
                        
                        <div class="feature">
                            <strong>🤖 Consultas RAG</strong><br>
                            Faça até 50 perguntas mensais sobre os documentos
                        </div>
                        
                        <p style="text-align: center;">
                            <a href="{dashboard_url}" class="button">Acessar Dashboard</a>
                        </p>
                        
                        <p>Se tiver dúvidas, nossa equipe está pronta para ajudar!</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 {self.from_name}. Todos os direitos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Texto simples como fallback
            text_body = f"""
            🎉 Bem-vindo ao {self.from_name}!
            
            Olá, {name}!
            
            Sua conta foi verificada com sucesso! Agora você tem acesso completo à nossa plataforma.
            
            🎁 Seu Trial Gratuito de 7 dias começou!
            Durante este período, você pode:
            
            🏢 Cadastrar suas empresas - Registre até 3 empresas para participar dos matches
            🔍 Matches automáticos - Receba até 100 matches mensais com licitações relevantes  
            🤖 Consultas RAG - Faça até 50 perguntas mensais sobre os documentos
            
            Acesse seu dashboard: {dashboard_url}
            
            Se tiver dúvidas, nossa equipe está pronta para ajudar!
            
            © 2024 {self.from_name}. Todos os direitos reservados.
            """
            
            return self._send_email(email, subject, text_body, html_body)
            
        except Exception as e:
            logger.error(f"Erro ao enviar email de boas-vindas: {e}")
            return False
    
    def send_verification_code(self, email: str, name: str, code: str) -> bool:
        """
        Enviar email com código de verificação
        
        Args:
            email: Email do destinatário
            name: Nome do usuário
            code: Código de verificação de 6 dígitos
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        try:
            subject = f"Seu código de verificação - {self.from_name}"
            
            # Template HTML do email
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 30px; background: #f9f9f9; }}
                    .code-box {{ 
                        background: #fff;
                        border: 2px dashed #007bff;
                        padding: 20px;
                        margin: 20px 0;
                        text-align: center;
                        font-size: 32px;
                        letter-spacing: 5px;
                        font-weight: bold;
                        color: #007bff;
                    }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{self.from_name}</h1>
                    </div>
                    <div class="content">
                        <h2>Olá, {name}!</h2>
                        <p>Bem-vindo ao {self.from_name}! Para começar a usar nossa plataforma, você precisa verificar seu email.</p>
                        <p>Use o código abaixo para verificar sua conta:</p>
                        <div class="code-box">
                            {code}
                        </div>
                        <p><strong>Este código expira em 10 minutos.</strong></p>
                        <p>Se você não criou uma conta conosco, pode ignorar este email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2024 {self.from_name}. Todos os direitos reservados.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Texto simples como fallback
            text_body = f"""
            Olá, {name}!
            
            Bem-vindo ao {self.from_name}! Para começar a usar nossa plataforma, você precisa verificar seu email.
            
            Seu código de verificação é: {code}
            
            Este código expira em 10 minutos.
            
            Se você não criou uma conta conosco, pode ignorar este email.
            
            © 2024 {self.from_name}. Todos os direitos reservados.
            """
            
            return self._send_email(email, subject, text_body, html_body)
            
        except Exception as e:
            logger.error(f"Erro ao enviar código de verificação: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
        """
        Enviar email via SMTP
        
        Args:
            to_email: Email do destinatário
            subject: Assunto do email
            text_body: Corpo do email em texto simples
            html_body: Corpo do email em HTML (opcional)
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        if not self.is_configured:
            # Simular envio no log se SMTP não configurado
            logger.info(f"📧 EMAIL SIMULADO para {to_email}")
            logger.info(f"Assunto: {subject}")
            logger.info(f"Conteúdo:\n{text_body}")
            return True
        
        try:
            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Adicionar corpo em texto simples
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Adicionar corpo em HTML se fornecido
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Conectar e enviar
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email enviado com sucesso para {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            if "Username and Password not accepted" in str(e):
                logger.error(f"❌ ERRO SMTP 535 - Credenciais não aceitas para {to_email}")
                logger.error("🔧 SOLUÇÃO: Configure uma 'Senha de App' do Google:")
                logger.error("   1. Habilite 2FA na conta Google")
                logger.error("   2. Gere senha de app em myaccount.google.com > Segurança > Senhas de app")
                logger.error("   3. Substitua SMTP_PASSWORD no config.env pela senha de 16 dígitos")
                logger.error(f"   Erro técnico: {e}")
            else:
                logger.error(f"Erro de autenticação SMTP para {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar email para {to_email}: {e}")
            return False 