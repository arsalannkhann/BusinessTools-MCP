#!/bin/bash
# AWS Deployment Script for MCP Server with Gemini TTS Interface

set -e

# Configuration
STACK_NAME="mcp-server-stack"
REGION="us-east-1"
DOMAIN_NAME="mcp.yourdomain.com"  # Change this to your domain
CERTIFICATE_ARN=""  # Add your ACM certificate ARN

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    if ! command -v aws &> /dev/null; then
        echo_error "AWS CLI is not installed"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo_error "AWS credentials not configured"
        exit 1
    fi
    
    echo_success "Prerequisites check passed"
}

# Build and push Docker image
build_and_push_image() {
    echo_info "Building and pushing Docker image..."
    
    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/mcp-server"
    
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories --repository-names mcp-server --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name mcp-server --region $REGION
    
    # Get ECR login
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO
    
    # Build image with both MCP server and TTS interface
    docker build -t mcp-server:latest .
    docker tag mcp-server:latest $ECR_REPO:latest
    
    # Push to ECR
    docker push $ECR_REPO:latest
    
    echo_success "Docker image pushed to ECR: $ECR_REPO:latest"
}

# Deploy CloudFormation stack
deploy_infrastructure() {
    echo_info "Deploying infrastructure with CloudFormation..."
    
    if [ -z "$CERTIFICATE_ARN" ]; then
        echo_warning "Certificate ARN not provided. You'll need to add it manually."
        echo_info "Create an ACM certificate for $DOMAIN_NAME first."
    fi
    
    aws cloudformation deploy \
        --template-file deployment/aws/cloudformation-template.yml \
        --stack-name $STACK_NAME \
        --parameter-overrides \
            DomainName=$DOMAIN_NAME \
            CertificateArn=$CERTIFICATE_ARN \
            Environment=production \
        --capabilities CAPABILITY_IAM \
        --region $REGION
    
    echo_success "Infrastructure deployed successfully"
}

# Setup secrets
setup_secrets() {
    echo_info "Setting up AWS Secrets Manager..."
    
    echo_warning "You need to manually populate these secrets:"
    echo "1. mcp-server/gemini-api-key - Your Gemini API key"
    echo "2. mcp-server/google-search-api-key - Your Google Search API key"
    echo "3. mcp-server/google-credentials - Your Google OAuth credentials JSON"
    echo "4. mcp-server/twilio-account-sid - Your Twilio Account SID"
    echo "5. mcp-server/twilio-auth-token - Your Twilio Auth Token"
    echo "6. mcp-server/hubspot-access-token - Your HubSpot Access Token"
    echo "7. mcp-server/apollo-api-key - Your Apollo API key"
    
    echo_info "Use AWS Console or CLI to populate secrets:"
    echo "aws secretsmanager put-secret-value --secret-id mcp-server/gemini-api-key --secret-string 'your-api-key'"
}

# Update ECS service
update_service() {
    echo_info "Updating ECS service..."
    
    CLUSTER_NAME="${STACK_NAME}-cluster"
    SERVICE_NAME="${STACK_NAME}-service"
    
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $REGION
    
    echo_info "Waiting for service to stabilize..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION
    
    echo_success "Service updated successfully"
}

# Get deployment info
get_deployment_info() {
    echo_info "Getting deployment information..."
    
    ALB_DNS=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
        --output text)
    
    TTS_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`TTSInterfaceURL`].OutputValue' \
        --output text)
    
    MCP_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`MCPServerURL`].OutputValue' \
        --output text)
    
    echo_success "Deployment completed successfully!"
    echo ""
    echo "🌐 Load Balancer DNS: $ALB_DNS"
    echo "🎤 TTS Interface URL: $TTS_URL"
    echo "🔧 MCP Server API URL: $MCP_URL"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Point your domain $DOMAIN_NAME to $ALB_DNS"
    echo "2. Populate AWS Secrets Manager with your API keys"
    echo "3. Test the TTS interface at $TTS_URL"
}

# Main deployment function
main() {
    echo_info "Starting AWS deployment for MCP Server with Gemini TTS Interface"
    
    case "${1:-all}" in
        "check")
            check_prerequisites
            ;;
        "build")
            check_prerequisites
            build_and_push_image
            ;;
        "deploy")
            check_prerequisites
            deploy_infrastructure
            setup_secrets
            ;;
        "update")
            check_prerequisites
            build_and_push_image
            update_service
            ;;
        "info")
            get_deployment_info
            ;;
        "all")
            check_prerequisites
            build_and_push_image
            deploy_infrastructure
            setup_secrets
            get_deployment_info
            ;;
        *)
            echo "Usage: $0 {check|build|deploy|update|info|all}"
            echo ""
            echo "Commands:"
            echo "  check   - Check prerequisites"
            echo "  build   - Build and push Docker image"
            echo "  deploy  - Deploy infrastructure"
            echo "  update  - Update service with new image"
            echo "  info    - Get deployment information"
            echo "  all     - Run complete deployment (default)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
