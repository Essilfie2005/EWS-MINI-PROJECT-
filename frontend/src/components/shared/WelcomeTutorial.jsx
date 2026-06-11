import { useState, useEffect } from 'react';
import { ChevronRight, ChevronLeft, X } from 'lucide-react';

export default function WelcomeTutorial({ forceShow = false, onClose }) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    const hasSeen = localStorage.getItem('ews_tutorial_seen');
    if (!hasSeen || forceShow) {
      // Add a slight delay for dramatic effect on first load
      const timer = setTimeout(() => setIsOpen(true), 800);
      return () => clearTimeout(timer);
    }
  }, [forceShow]);

  if (!isOpen) return null;

  const slides = [
    {
      title: "Welcome to the EWS",
      desc: "Identify at-risk students before it's too late. Our AI analyzes attendance, quizzes, and engagement to provide early warnings.",
      img: "/assets/slide1.png"
    },
    {
      title: "Understand the 'Why'",
      desc: "Don't just trust a black box. Our SHAP-powered risk profiles show you exactly which factors are pushing a student toward dropping out.",
      img: "/assets/slide2.png"
    },
    {
      title: "Take Immediate Action",
      desc: "Reach students where they are. Instantly trigger SMS or WhatsApp alerts to counsellors or students directly from the dashboard.",
      img: "/assets/slide3.png"
    }
  ];

  const handleNext = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide(prev => prev + 1);
    } else {
      handleClose();
    }
  };

  const handlePrev = () => {
    if (currentSlide > 0) {
      setCurrentSlide(prev => prev - 1);
    }
  };

  const handleClose = () => {
    setClosing(true);
    localStorage.setItem('ews_tutorial_seen', 'true');
    setTimeout(() => {
      setIsOpen(false);
      if (onClose) onClose();
    }, 400); // match animation duration
  };

  return (
    <div className={`tutorial-overlay fade-in ${closing ? 'fade-out' : ''}`}>
      <div className={`tutorial-modal slide-up ${closing ? 'slide-down' : ''}`}>
        
        <button className="tutorial-close" onClick={handleClose}>
          <X size={20} />
        </button>

        <div className="tutorial-image-container">
          {slides.map((slide, i) => (
            <img 
              key={i}
              src={slide.img} 
              alt={slide.title}
              className={`tutorial-image ${i === currentSlide ? 'active' : ''}`}
              style={{ opacity: i === currentSlide ? 1 : 0, transition: 'opacity 0.5s ease-in-out' }}
            />
          ))}
        </div>

        <div className="tutorial-content">
          <h2 className="tutorial-title">{slides[currentSlide].title}</h2>
          <p className="tutorial-desc">{slides[currentSlide].desc}</p>
        </div>

        <div className="tutorial-footer">
          <div className="tutorial-dots">
            {slides.map((_, i) => (
              <div 
                key={i} 
                className={`tutorial-dot ${i === currentSlide ? 'active' : ''}`}
                onClick={() => setCurrentSlide(i)}
              />
            ))}
          </div>

          <div className="tutorial-actions">
            {currentSlide > 0 && (
              <button className="btn btn-secondary btn-sm" onClick={handlePrev}>
                <ChevronLeft size={16} /> Back
              </button>
            )}
            <button className="btn btn-primary btn-sm" onClick={handleNext}>
              {currentSlide === slides.length - 1 ? 'Get Started' : 'Next'} {currentSlide < slides.length - 1 && <ChevronRight size={16} />}
            </button>
          </div>
        </div>

      </div>

      <style>{`
        .tutorial-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(10, 12, 16, 0.85);
          backdrop-filter: blur(8px);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .tutorial-modal {
          background: rgba(20, 24, 32, 0.95);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          width: 100%;
          max-width: 480px;
          box-shadow: 0 24px 48px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
          overflow: hidden;
          position: relative;
        }
        .tutorial-close {
          position: absolute;
          top: 16px;
          right: 16px;
          background: rgba(0,0,0,0.4);
          border: none;
          color: rgba(255,255,255,0.6);
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          z-index: 10;
          transition: all 0.2s;
        }
        .tutorial-close:hover {
          background: rgba(255,255,255,0.1);
          color: #fff;
        }
        .tutorial-image-container {
          width: 100%;
          height: 280px;
          position: relative;
          background: #000;
          overflow: hidden;
        }
        .tutorial-image {
          position: absolute;
          top: 0; left: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .tutorial-content {
          padding: 32px 24px 16px;
          text-align: center;
        }
        .tutorial-title {
          font-size: 1.4rem;
          font-weight: 600;
          margin-bottom: 12px;
          color: #fff;
        }
        .tutorial-desc {
          font-size: 0.95rem;
          color: rgba(255, 255, 255, 0.7);
          line-height: 1.6;
          min-height: 70px;
        }
        .tutorial-footer {
          padding: 16px 24px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .tutorial-dots {
          display: flex;
          gap: 6px;
        }
        .tutorial-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          cursor: pointer;
          transition: all 0.3s;
        }
        .tutorial-dot.active {
          background: var(--accent);
          width: 20px;
          border-radius: 4px;
        }
        .tutorial-actions {
          display: flex;
          gap: 12px;
        }
        .fade-out {
          animation: fadeOut 0.4s forwards;
        }
        .slide-down {
          animation: slideDown 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes fadeOut {
          to { opacity: 0; }
        }
        @keyframes slideDown {
          to { transform: translateY(30px); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
