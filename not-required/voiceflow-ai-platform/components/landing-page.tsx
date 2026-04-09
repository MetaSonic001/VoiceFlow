"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import FeatureCard from "@/components/ui/FeatureCard"
import TestimonialCarousel from '@/components/ui/TestimonialCarousel'
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { AuthModal } from "@/components/auth-modal"
import { HelpFlowModal } from "@/components/help-flow-modal"
import {
  Phone,
  MessageSquare,
  Brain,
  Zap,
  Shield,
  BarChart3,
  Play,
  ArrowRight,
  CheckCircle,
  Globe,
  Sparkles,
  HelpCircle,
  TrendingUp,
  DollarSign,
  MapPin,
  ExternalLink,
} from "lucide-react"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from 'framer-motion'
import MotionWrapper, { containerVariants, itemVariants, MOTION } from '@/components/ui/MotionWrapper'
import BentoGrid from '@/components/ui/BentoGrid'
import MorphingBlob from '@/components/ui/MorphingBlob'
import useParallax from '@/components/hooks/useParallax'
import ParallaxBlob from '@/components/ui/ParallaxBlob'
import FloatingActionPanel from '@/components/ui/FloatingActionPanel'
import MagneticButton from '@/components/ui/MagneticButton'

export function LandingPage() {
  const [showAuth, setShowAuth] = useState(false)
  const [authMode, setAuthMode] = useState<"login" | "signup">("signup")
  const [showHelpFlow, setShowHelpFlow] = useState(false)
  const [currentTestimonial, setCurrentTestimonial] = useState(0)
  const router: Router= useRouter()

  const testimonials = [
    {
      name: "Rajesh Kumar",
      company: "TechStart India",
      role: "CEO",
      content:
        "VoiceFlow AI reduced our customer support costs by 70% while improving response times. Game-changer for Indian startups!",
      rating: 5,
    },
    {
      name: "Priya Sharma",
      company: "FinanceFlow",
      role: "Operations Head",
      content: "Our Hindi-speaking customers love the natural conversations. Perfect for the Indian market.",
      rating: 5,
    },
    {
      name: "Amit Patel",
      company: "EcomGrow",
      role: "Founder",
      content: "From setup to deployment in 10 minutes. The ROI was visible within the first week.",
      rating: 5,
    },
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTestimonial((prev) => (prev + 1) % testimonials.length)
    }, 4000)
    return () => clearInterval(interval)
  }, [testimonials.length])

  const handleGetStarted = () => {
    setAuthMode("signup")
    setShowAuth(true)
  }

  const handleSignIn = () => {
    setAuthMode("login")
    setShowAuth(true)
  }

  const handleWatchDemo = () => {
    window.open("https://www.youtube.com/watch?v=demo", "_blank")
  }

  const handleScheduleDemo = () => {
    window.open("https://calendly.com/voiceflow-ai/demo", "_blank")
  }

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId)
    if (element) {
      element.scrollIntoView({ behavior: "smooth" })
    }
  }

  return (
    <MotionWrapper className="min-h-screen bg-background overflow-hidden">
  <header className="fixed top-0 w-full z-50 glass-effect border-b border-border/50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-gradient-to-r from-primary to-accent rounded-xl flex items-center justify-center animate-glow">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              VoiceFlow AI
            </span>
          </div>
          <nav className="hidden md:flex items-center space-x-8">
            <button
              onClick={() => scrollToSection("features")}
              className="text-muted-foreground hover:text-primary transition-all duration-300 hover:scale-105"
            >
              Features
            </button>
            <button
              onClick={() => scrollToSection("pricing")}
              className="text-muted-foreground hover:text-primary transition-all duration-300 hover:scale-105"
            >
              Pricing
            </button>
            <button
              onClick={() => scrollToSection("indian-market")}
              className="text-muted-foreground hover:text-primary transition-all duration-300 hover:scale-105"
            >
              India Focus
            </button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowHelpFlow(true)}
              className="text-muted-foreground hover:text-primary"
            >
              <HelpCircle className="w-4 h-4 mr-2" />
              How it Works
            </Button>
            <Button variant="ghost" onClick={handleSignIn} className="hover:scale-105 transition-transform">
              Sign In
            </Button>
            <Button
              onClick={handleGetStarted}
              className="bg-gradient-to-r from-primary to-accent hover:scale-105 transition-transform shadow-lg"
            >
              Get Started
            </Button>
          </nav>
          <div className="md:hidden">
            <Button variant="ghost" size="sm" onClick={() => setShowHelpFlow(true)}>
              <HelpCircle className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      <section className="pt-32 pb-20 px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-accent/5"></div>
        <div className="container mx-auto text-center max-w-6xl relative">
          <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
            <motion.div variants={itemVariants} className="animate-float">
              <Badge
                variant="secondary"
                className="mb-6 px-4 py-2 text-sm font-semibold bg-gradient-to-r from-primary/10 to-accent/10 border-primary/20"
              >
                <Sparkles className="w-4 h-4 mr-2" />
                Next-Generation AI Platform • Trusted by 10,000+ Businesses
              </Badge>
            </motion.div>

            <motion.h1 variants={itemVariants} className="text-5xl md:text-7xl font-bold text-balance mb-8 leading-tight">
              Create Intelligent
              <span className="bg-gradient-to-r from-primary via-accent to-secondary bg-clip-text text-transparent animate-pulse">
                {" "}
                Voice & Chat Agents{" "}
              </span>
              in Minutes
            </motion.h1>

            <motion.p variants={itemVariants} className="text-xl md:text-2xl text-muted-foreground text-balance mb-12 max-w-4xl mx-auto leading-relaxed">
              Transform your business with AI agents that handle customer support, sales calls, and internal workflows.
              <strong className="text-foreground"> No coding required</strong> - just upload your knowledge and go live.
            </motion.p>

            <motion.div variants={itemVariants} className="flex flex-col sm:flex-row gap-6 justify-center mb-8">
              <MagneticButton onClick={handleGetStarted} className="text-lg px-10 py-4 bg-gradient-to-r from-primary to-accent text-white shadow-2xl">
                <Play className="w-5 h-5 mr-2" />
                Start Free Trial
              </MagneticButton>
              <MagneticButton onClick={handleWatchDemo} className="text-lg px-10 py-4 border-2 bg-transparent">
                <Play className="w-5 h-5 mr-2" />
                Watch Demo
                <ExternalLink className="w-4 h-4 ml-2" />
              </MagneticButton>
            </motion.div>
          </motion.div>

          {/* Testimonials */}
          <div className="mt-12">
            {/* lightweight testimonial carousel */}
            <TestimonialCarousel
              items={testimonials.map(t => ({ name: t.name, company: t.company, content: t.content }))}
            />
          </div>

          <ParallaxBlob />

          <div className="flex flex-wrap justify-center gap-6 text-sm text-muted-foreground mb-16">
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
              No credit card required
            </div>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
              14-day free trial
            </div>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
              Setup in under 5 minutes
            </div>
          </div>

          <div className="grid md:grid-cols-4 gap-8 max-w-4xl mx-auto">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">10,000+</div>
              <div className="text-sm text-muted-foreground">Active Businesses</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">2M+</div>
              <div className="text-sm text-muted-foreground">Conversations Handled</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">99.9%</div>
              <div className="text-sm text-muted-foreground">Uptime</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">5 Min</div>
              <div className="text-sm text-muted-foreground">Average Setup</div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="py-24 px-4 bg-gradient-to-b from-muted/30 to-background">
        <div className="container mx-auto">
          <div className="text-center mb-20">
            <Badge variant="outline" className="mb-4">
              <Zap className="w-4 h-4 mr-2" />
              Powerful Features
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-6">Everything You Need to Build AI Agents</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              From document upload to live deployment, our platform handles the complexity so you can focus on your
              business.
            </p>
          </div>

          <div className="">
            <BentoGrid
              items={[
                {
                  icon: Phone,
                  title: "Voice & Phone Integration",
                  description:
                    "Get dedicated phone numbers with lifelike TTS voices. Handle inbound and outbound calls seamlessly.",
                  color: "blue",
                },
                {
                  icon: MessageSquare,
                  title: "Multi-Channel Support",
                  description: "Deploy across voice, chat widgets, WhatsApp, and more. One agent, multiple touchpoints.",
                  color: "green",
                },
                {
                  icon: Brain,
                  title: "Smart Knowledge Base",
                  description:
                    "Upload PDFs, FAQs, and documents. Your agent learns from your content and stays up-to-date.",
                  color: "purple",
                },
                {
                  icon: Zap,
                  title: "5-Minute Setup",
                  description:
                    "From signup to live agent in minutes. No technical expertise required with our guided wizard.",
                  color: "yellow",
                },
                {
                  icon: Shield,
                  title: "Enterprise Security",
                  description: "GDPR & HIPAA ready with end-to-end encryption. Your data stays private and secure.",
                  color: "red",
                },
                {
                  icon: BarChart3,
                  title: "Advanced Analytics",
                  description:
                    "Track performance, monitor conversations, and optimize your agents with detailed insights.",
                  color: "indigo",
                },
              ]}
            />
          </div>
        </div>
      </section>

      <section id="indian-market" className="py-24 px-4 bg-gradient-to-r from-primary/5 to-accent/5">
        <div className="container mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <Badge variant="secondary" className="mb-4">
                <MapPin className="w-4 h-4 mr-2" />
                Made for India
              </Badge>
              <h2 className="text-4xl md:text-5xl font-bold mb-6">Built for the Indian Market</h2>
              <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
                We understand the unique needs of Indian businesses. From multilingual support to local payment
                integration, VoiceFlow AI is designed to help Indian companies scale globally.
              </p>

              <div className="space-y-4 mb-8">
                {[
                  "Hindi, English, and 10+ Indian languages supported",
                  "Integration with UPI, Razorpay, and local payment gateways",
                  "Compliance with Indian data protection laws",
                  "24/7 support in Indian time zones",
                  "Pricing in INR with flexible payment options",
                ].map((feature, index) => (
                  <div key={index} className="flex items-center space-x-3">
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                    <span className="text-foreground">{feature}</span>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="text-center p-4 bg-card rounded-xl border">
                  <TrendingUp className="w-8 h-8 text-primary mx-auto mb-2" />
                  <div className="text-2xl font-bold text-primary">70%</div>
                  <div className="text-sm text-muted-foreground">Cost Reduction</div>
                </div>
                <div className="text-center p-4 bg-card rounded-xl border">
                  <DollarSign className="w-8 h-8 text-primary mx-auto mb-2" />
                  <div className="text-2xl font-bold text-primary">₹999</div>
                  <div className="text-sm text-muted-foreground">Starting Price/Month</div>
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-primary to-accent rounded-3xl blur-3xl opacity-20"></div>
              <Card className="relative bg-card/80 backdrop-blur-sm border-2">
                <CardHeader>
                  <CardTitle className="text-center text-2xl mb-6">Indian Business Success</CardTitle>
                  <div className="space-y-6">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                        <Globe className="w-6 h-6 text-green-600" />
                      </div>
                      <div>
                        <div className="font-semibold">Multilingual Support</div>
                        <div className="text-sm text-muted-foreground">Serve customers in their preferred language</div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                        <Shield className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <div className="font-semibold">Data Localization</div>
                        <div className="text-sm text-muted-foreground">
                          Your data stays in India, compliant with local laws
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                        <DollarSign className="w-6 h-6 text-purple-600" />
                      </div>
                      <div>
                        <div className="font-semibold">Affordable Pricing</div>
                        <div className="text-sm text-muted-foreground">
                          Competitive rates designed for Indian businesses
                        </div>
                      </div>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            </div>
          </div>
        </div>
      </section>

      <section id="pricing" className="py-24 px-4 bg-muted/30">
        <div className="container mx-auto">
          <div className="text-center mb-20">
            <Badge variant="outline" className="mb-4">
              <DollarSign className="w-4 h-4 mr-2" />
              Simple Pricing
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-6">Choose Your Plan</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Transparent pricing designed for Indian businesses. No hidden fees, no surprises.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              {
                name: "Starter",
                price: "₹999",
                period: "/month",
                description: "Perfect for small businesses",
                features: [
                  "1 AI Agent",
                  "1,000 conversations/month",
                  "Basic analytics",
                  "Email support",
                  "Hindi + English support",
                ],
                popular: false,
              },
              {
                name: "Professional",
                price: "₹2,999",
                period: "/month",
                description: "Most popular for growing companies",
                features: [
                  "5 AI Agents",
                  "10,000 conversations/month",
                  "Advanced analytics",
                  "Priority support",
                  "All Indian languages",
                  "WhatsApp integration",
                  "Custom voice training",
                ],
                popular: true,
              },
              {
                name: "Enterprise",
                price: "Custom",
                period: "",
                description: "For large organizations",
                features: [
                  "Unlimited AI Agents",
                  "Unlimited conversations",
                  "Custom integrations",
                  "Dedicated support",
                  "On-premise deployment",
                  "SLA guarantee",
                  "Custom compliance",
                ],
                popular: false,
              },
            ].map((plan, index) => (
              <Card
                key={index}
                className={`relative ${plan.popular ? "border-primary border-2 scale-105" : ""} hover:shadow-2xl transition-all duration-300`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-gradient-to-r from-primary to-accent text-white">Most Popular</Badge>
                  </div>
                )}
                <CardHeader className="text-center p-8">
                  <CardTitle className="text-2xl mb-2">{plan.name}</CardTitle>
                  <div className="mb-4">
                    <span className="text-4xl font-bold text-primary">{plan.price}</span>
                    <span className="text-muted-foreground">{plan.period}</span>
                  </div>
                  <CardDescription className="text-base mb-6">{plan.description}</CardDescription>

                  <div className="space-y-3 mb-8">
                    {plan.features.map((feature, featureIndex) => (
                      <div key={featureIndex} className="flex items-center text-sm">
                        <CheckCircle className="w-4 h-4 text-green-500 mr-3 flex-shrink-0" />
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>

                  <Button
                    onClick={handleGetStarted}
                    className={`w-full ${plan.popular ? "bg-gradient-to-r from-primary to-accent" : ""}`}
                    variant={plan.popular ? "default" : "outline"}
                  >
                    {plan.name === "Enterprise" ? "Contact Sales" : "Start Free Trial"}
                  </Button>
                </CardHeader>
              </Card>
            ))}
          </div>

          <div className="text-center mt-12">
            <p className="text-muted-foreground mb-4">
              All plans include 14-day free trial • No setup fees • Cancel anytime
            </p>
            <Button variant="ghost" onClick={() => setShowHelpFlow(true)}>
              <HelpCircle className="w-4 h-4 mr-2" />
              Need help choosing? Talk to our experts
            </Button>
          </div>
        </div>
      </section>

      <section className="py-24 px-4 gradient-bg text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-black/20"></div>
        <div className="container mx-auto text-center relative">
          <h2 className="text-4xl md:text-6xl font-bold mb-6">Ready to Transform Your Business?</h2>
          <p className="text-xl md:text-2xl mb-12 opacity-90 max-w-3xl mx-auto leading-relaxed">
            Join 10,000+ businesses already using AI agents to improve customer experience and reduce operational costs.
            <strong> Start your transformation today!</strong>
          </p>

          <div className="flex flex-col sm:flex-row gap-6 justify-center mb-8">
            <Button
              size="lg"
              variant="secondary"
              onClick={handleGetStarted}
              className="text-lg px-12 py-4 bg-white text-primary hover:scale-110 transition-all duration-300 shadow-2xl font-semibold"
            >
              Start Free Trial Now
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={handleScheduleDemo}
              className="text-lg px-12 py-4 border-white text-white hover:bg-white hover:text-primary hover:scale-110 transition-all duration-300 bg-transparent"
            >
              Schedule Demo
              <ExternalLink className="w-4 h-4 ml-2" />
            </Button>
          </div>

          <p className="text-sm opacity-75">
            🚀 Limited Time: Get 50% off your first 3 months • No setup fees • Cancel anytime
          </p>
        </div>
      </section>

      <footer className="py-16 px-4 border-t border-border bg-muted/30">
        <div className="container mx-auto">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-8 h-8 bg-gradient-to-r from-primary to-accent rounded-lg flex items-center justify-center">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold">VoiceFlow AI</span>
              </div>
              <p className="text-muted-foreground mb-4">Empowering Indian businesses with intelligent AI agents.</p>
              <div className="flex space-x-4">
                <Badge variant="outline">Made in India</Badge>
                <Badge variant="outline">ISO Certified</Badge>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <div className="space-y-2 text-sm text-muted-foreground">
                <button
                  onClick={() => scrollToSection("features")}
                  className="block hover:text-foreground transition-colors"
                >
                  Features
                </button>
                <button
                  onClick={() => scrollToSection("pricing")}
                  className="block hover:text-foreground transition-colors"
                >
                  Pricing
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  API Documentation
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Integrations
                </button>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <div className="space-y-2 text-sm text-muted-foreground">
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  About Us
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Careers
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Contact
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Blog
                </button>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Support</h3>
              <div className="space-y-2 text-sm text-muted-foreground">
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Help Center
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Community
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Status
                </button>
                <button onClick={() => setShowHelpFlow(true)} className="block hover:text-foreground transition-colors">
                  Security
                </button>
              </div>
            </div>
          </div>

          <div className="border-t border-border pt-8 text-center text-muted-foreground">
            <p>&copy; 2024 VoiceFlow AI. All rights reserved. Made with ❤️ in India.</p>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <AuthModal open={showAuth} onOpenChange={setShowAuth} mode={authMode} onModeChange={setAuthMode} />
      <HelpFlowModal open={showHelpFlow} onOpenChange={setShowHelpFlow} />
      <FloatingActionPanel>
        <Button size="sm" onClick={() => scrollToSection('features')} className="bg-gradient-to-r from-primary to-accent text-white">
          Explore Features
        </Button>
      </FloatingActionPanel>
    </MotionWrapper>
  )
}
